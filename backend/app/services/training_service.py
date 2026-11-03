"""
Training orchestration service (Volume II Chapter 10.2 Execution Flow).

This is the service that runs the full sequence:
cleaning -> features -> causal_graph (DoWhy) -> dml_model (EconML) ->
optimizer (SciPy) -> persist everything, plus (enhancement additions)
data drift detection against the previous completed run, and global
feature importances for the Explainability panel.

Owned by Member 4 (Team Lead, Volume II Chapter 4.4), with ML-specific
logic contributed by Member 1 and Member 2 (Volume II Chapter 4.1-4.2).
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DatasetNotFoundError
from app.core.logging import get_logger
from app.pipeline import causal_graph, cleaning, dml_model, drift_detector, explainability, features, optimizer, propensity_score
from app.pipeline.propensity_score import PropensityResult
from app.models.propensity_diagnostic import PropensityDiagnostic
from app.models.recommendation_result import RecommendationResult
from app.repositories import (
    allocation_repository,
    balance_metric_repository,
    customer_repository,
    dataset_repository,
    drift_repository,
    feature_importance_repository,
    ite_repository,
    propensity_diagnostic_repository,
    propensity_repository,
    refutation_repository,
    recommendation_repository,
    run_repository,
)
from app.schemas.run_schema import RunCreateSchema, RunResponseSchema

logger = get_logger(__name__)


def _propensity_result_to_diagnostics(result: PropensityResult) -> List[PropensityDiagnostic]:
    diagnostics: List[PropensityDiagnostic] = []
    if result.binary and result.binary.overlap:
        o = result.binary.overlap
        diagnostics.append(PropensityDiagnostic(
            run_id=0,
            metric_name="overlap_summary",
            metric_value=o.pct_outside_support,
            details_json=json.dumps({
                "min_propensity": o.min_propensity,
                "max_propensity": o.max_propensity,
                "common_support_min": o.common_support_min,
                "common_support_max": o.common_support_max,
                "n_total": o.n_total,
                "n_outside_support": o.n_outside_support,
                "pct_outside_support": o.pct_outside_support,
                "n_extreme_low": o.n_extreme_low,
                "n_extreme_high": o.n_extreme_high,
                "pct_extreme": o.pct_extreme,
            }),
        ))
    if result.binary and result.binary.matching:
        m = result.binary.matching
        diagnostics.append(PropensityDiagnostic(
            run_id=0,
            metric_name="matching_summary",
            metric_value=float(m.n_matched_pairs),
            details_json=json.dumps({
                "method": m.method,
                "n_treated": m.n_treated,
                "n_control": m.n_control,
                "n_matched_pairs": m.n_matched_pairs,
                "n_unmatched_treated": m.n_unmatched_treated,
                "n_unmatched_control": m.n_unmatched_control,
                "caliper": m.caliper,
                "replacement": m.replacement,
                "matched_treated_indices": m.matched_treated_indices,
                "matched_control_indices": m.matched_control_indices,
            }),
        ))
    for w in result.warnings:
        diagnostics.append(PropensityDiagnostic(
            run_id=0,
            metric_name="warning",
            metric_value=0.0,
            details_json=json.dumps({"message": w}),
        ))
    return diagnostics


def _log_timing(timing: Dict[str, float], total: float) -> None:
    stages = [
        ("Data loading", "data_loading"),
        ("Cleaning + features", "cleaning_features"),
        ("Propensity", "propensity"),
        ("Drift", "drift"),
        ("DoWhy + refutation", "causal_refutation"),
        ("Explainability", "explainability"),
        ("DML + ITE", "dml_ite"),
        ("Optimization", "optimization"),
        ("Persistence", "persistence"),
        ("Recommendation cache", "recommendation_cache"),
    ]
    logger.info("EconoCausal Pipeline Timing")
    logger.info("--------------------------------")
    for label, key in stages:
        val = timing.get(key, 0.0)
        pct = (val / total * 100.0) if total > 0 else 0.0
        logger.info(f"{label:25s} {val:6.2f}s ({pct:5.1f}%)")
    logger.info("--------------------------------")
    logger.info(f"{'TOTAL':25s} {total:6.2f}s (100.0%)")


def create_run(db: Session, payload: RunCreateSchema, owner_id: Optional[int] = None) -> RunResponseSchema:
    """Run the full causal pipeline synchronously and persist all results.

    In a production deployment this would be dispatched to a background
    worker; for this internship's local-only scope (Volume II Chapter
    1.10), running synchronously keeps the system simple to demo.
    """
    dataset = dataset_repository.get(db, payload.dataset_id)
    if dataset is None:
        raise DatasetNotFoundError(f"No dataset with id {payload.dataset_id}.")
    if owner_id is not None and dataset.owner_id != owner_id:
        raise DatasetNotFoundError(f"No dataset with id {payload.dataset_id}.")

    discount_levels: List[float] = payload.discount_levels or list(settings.candidate_discount_levels)

    run = run_repository.create(
        db,
        payload.dataset_id,
        payload.budget,
        payload.base_estimator,
        campaign_name=payload.campaign_name,
        discount_levels=discount_levels,
        treatment_column=payload.treatment_column,
        outcome_column=payload.outcome_column,
        owner_id=owner_id,
    )
    logger.info("Run %d created for dataset %d", run.run_id, payload.dataset_id)

    timing: Dict[str, float] = {}
    total_start = time.time()

    try:
        # Stage: data_loading
        t0 = time.time()
        customers = customer_repository.list_by_dataset(db, payload.dataset_id)
        df = customer_repository.to_dataframe(customers)
        timing["data_loading"] = time.time() - t0

        # The Customer table always stores treatment/outcome under the
        # normalized keys "treatment" / "outcome" (see
        # customer_repository.to_dataframe).  run.treatment_column and
        # run.outcome_column record the user's original CSV headers for
        # metadata/history purposes, but the pipeline must use the fixed
        # column names that actually exist in the reconstructed DataFrame.
        treatment_col = "treatment"
        outcome_col = "outcome"

        # Stage: cleaning_features
        t0 = time.time()
        df_clean = cleaning.clean(df, treatment_col=treatment_col, outcome_col=outcome_col)
        cleaning.validate_treatment_variation(df_clean, treatment_col=treatment_col)
        feature_set = features.engineer(df_clean, treatment_col=treatment_col, outcome_col=outcome_col)
        customer_ids = df_clean["customer_id"].tolist() if "customer_id" in df_clean.columns else list(range(len(df_clean)))
        timing["cleaning_features"] = time.time() - t0

        # Stage: propensity
        t0 = time.time()
        try:
            propensity_result = propensity_score.run_propensity_analysis(feature_set)
            if propensity_result.binary:
                binary = propensity_result.binary
                matched_indices = []
                matched_pair_map = {}
                if binary.matching and binary.matching.n_matched_pairs > 0:
                    m = binary.matching
                    matched_indices = sorted(set(list(m.matched_treated_indices) + list(m.matched_control_indices)))
                    for t_idx, c_idx in zip(m.matched_treated_indices, m.matched_control_indices):
                        matched_pair_map[t_idx] = c_idx
                        matched_pair_map[c_idx] = t_idx
                propensity_repository.bulk_create_scores(
                    db,
                    run.run_id,
                    customer_ids,
                    binary.propensity_scores,
                    propensity_result.continuous.predicted_treatment if propensity_result.continuous else [0.0] * len(customer_ids),
                    matched_indices,
                    matched_pair_map,
                )
                all_balance = []
                if binary.balance:
                    all_balance.extend(binary.balance)
                if propensity_result.continuous and propensity_result.continuous.balance:
                    all_balance.extend(propensity_result.continuous.balance)
                if all_balance:
                    balance_metric_repository.bulk_create(db, run.run_id, all_balance)
                diags = _propensity_result_to_diagnostics(propensity_result)
                for d in diags:
                    d.run_id = run.run_id
                propensity_diagnostic_repository.bulk_create(db, run.run_id, diags)
        except Exception:  # pragma: no cover - propensity diagnostics must never block a run
            logger.exception("Propensity analysis skipped for run %d due to an error", run.run_id)
        timing["propensity"] = time.time() - t0

        # Stage: drift
        t0 = time.time()
        try:
            reference_run = run_repository.most_recent_completed_before(db, run.run_id)
            if reference_run is not None:
                ref_customers = customer_repository.list_by_dataset(db, reference_run.dataset_id)
                ref_df = customer_repository.to_dataframe(ref_customers)
                ref_clean = cleaning.clean(ref_df)
                ref_feature_set = features.engineer(ref_clean)
                drift_reports = drift_detector.detect_drift(ref_feature_set.X, feature_set.X)
                if drift_reports:
                    drift_repository.bulk_create(db, run.run_id, drift_reports)
        except Exception:  # pragma: no cover - drift check must never block a run
            logger.exception("Drift detection skipped for run %d due to an error", run.run_id)
        timing["drift"] = time.time() - t0

        # Stage: causal_refutation
        t0 = time.time()
        model_df = feature_set.X.copy()
        model_df[treatment_col] = feature_set.T
        model_df[outcome_col] = feature_set.Y
        causal_model = causal_graph.build_model(model_df, feature_set.feature_names, treatment_col=treatment_col, outcome_col=outcome_col)
        identified, estimate = causal_graph.identify_and_estimate(causal_model)
        refutation_outcomes = causal_graph.run_refutation_tests(causal_model, identified, estimate)
        refutation_repository.bulk_create(db, run.run_id, refutation_outcomes)
        timing["causal_refutation"] = time.time() - t0

        # Stage: explainability
        t0 = time.time()
        try:
            importances = explainability.compute_feature_importance(feature_set.X, feature_set.Y)
            if importances:
                feature_importance_repository.bulk_create(db, run.run_id, importances)
        except Exception:  # pragma: no cover - explainability must never block a run
            logger.exception("Feature importance computation skipped for run %d", run.run_id)
        timing["explainability"] = time.time() - t0

        # Stage: dml_ite
        t0 = time.time()
        est = dml_model.train(feature_set, payload.base_estimator)
        predictions = dml_model.estimate_ite(est, feature_set, customer_ids, discount_levels=discount_levels)
        ite_repository.bulk_create(db, run.run_id, predictions)
        timing["dml_ite"] = time.time() - t0

        # Stage: optimization
        t0 = time.time()
        ite_matrix: dict = {}
        for p in predictions:
            ite_matrix.setdefault(p.customer_id, {})[p.discount_level] = p.ite_value
        allocations, _total_used = optimizer.allocate(ite_matrix, payload.budget)
        timing["optimization"] = time.time() - t0

        # Stage: persistence
        t0 = time.time()
        allocation_repository.bulk_create(db, run.run_id, allocations)
        timing["persistence"] = time.time() - t0

        run = run_repository.set_status(db, run, "complete")

        # Stage: recommendation_cache (after status is complete so the
        # service's guard clause allows computation).
        t0 = time.time()
        try:
            from app.services import recommendation_service
            rec_response = recommendation_service.get_recommendations(db, run.run_id)
            rows = []
            for rec in rec_response.recommendations:
                rows.append(RecommendationResult(
                    run_id=run.run_id,
                    customer_id=rec.customer_id,
                    recommended_discount=rec.recommended_discount,
                    expected_uplift=rec.expected_uplift,
                    purchase_probability=rec.purchase_probability,
                    confidence_score=rec.confidence_score,
                    confidence_level=rec.confidence_level,
                    confidence_interval=__import__("json").dumps(rec.confidence_interval) if rec.confidence_interval else None,
                    evidence=__import__("json").dumps(rec.evidence) if rec.evidence else None,
                     contributing_factors=__import__("json").dumps([f.model_dump() for f in rec.contributing_factors]) if rec.contributing_factors else None,
                ))
            recommendation_repository.bulk_create(db, rows)
        except Exception:  # pragma: no cover - recommendation cache must never block a run
            logger.exception("Recommendation caching skipped for run %d", run.run_id)
        timing["recommendation_cache"] = time.time() - t0

        total_elapsed = time.time() - total_start
        timing["total"] = total_elapsed
        logger.info("Run %d completed successfully", run.run_id)
    except Exception:
        run_repository.set_status(db, run, "failed")
        logger.exception("Run %d failed", run.run_id)
        raise

    _log_timing(timing, timing.get("total", time.time() - total_start))
    return _to_response(run)


def get_run(db: Session, run_id: int) -> RunResponseSchema:
    from app.core.exceptions import RunNotFoundError

    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    return _to_response(run)


def _to_response(run) -> RunResponseSchema:
    return RunResponseSchema(
        run_id=run.run_id,
        status=run.status,
        started_at=run.started_at,
        base_estimator=run.base_estimator,
        campaign_name=run.campaign_name,
        budget=run.budget,
        discount_levels=json.loads(run.discount_levels_json),
    )
