"""Vectorized version of the per-customer explanation, computed once for
every customer in a run so the recommendation panel (Enhancement #6) loads
in a single request instead of one call per row.

Optimized (Performance Audit): recommendation results are now persisted to
the `recommendation_results` table at run completion time. Subsequent GET
requests read the cached rows directly, avoiding repeated DataFrame cleaning,
feature engineering, and per-customer explanation on every request.
"""
from __future__ import annotations

import json
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.pipeline import cleaning, explainability, features
from app.repositories import (
    allocation_repository,
    customer_repository,
    feature_importance_repository,
    ite_repository,
    propensity_diagnostic_repository,
    refutation_repository,
    recommendation_repository,
    run_repository,
)
from app.schemas.explainability_schema import ContributingFactorSchema
from app.schemas.recommendation_schema import RecommendationItemSchema, RecommendationResponseSchema
from app.services.confidence_service import compute as compute_confidence, ConfidenceResult


def _extract_propensity_metrics(diagnostics) -> dict:
    pct_outside_support = 0.0
    pct_extreme = 0.0
    n_unmatched_treated = 0
    n_matched_pairs = 0
    for d in diagnostics:
        if d.metric_name == "overlap_summary" and d.details_json:
            try:
                details = json.loads(d.details_json)
                pct_outside_support = float(details.get("pct_outside_support", 0.0))
                pct_extreme = float(details.get("pct_extreme", 0.0))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        elif d.metric_name == "matching_summary" and d.details_json:
            try:
                details = json.loads(d.details_json)
                n_unmatched_treated = int(details.get("n_unmatched_treated", 0))
                n_matched_pairs = int(details.get("n_matched_pairs", 0))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    return {
        "pct_outside_support": pct_outside_support,
        "pct_extreme": pct_extreme,
        "n_unmatched_treated": n_unmatched_treated,
        "n_matched_pairs": n_matched_pairs,
    }


def _compute_recommendations(db: Session, run_id: int) -> RecommendationResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Recommendations not available until run {run_id} completes.")

    allocations = allocation_repository.list_by_run(db, run_id)
    ite_scores = ite_repository.list_by_run(db, run_id)
    ite_lookup: Dict[tuple, float] = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}
    ci_lookup: Dict[tuple, tuple] = {(s.customer_id, s.discount_level): (s.ci_lower, s.ci_upper) for s in ite_scores}
    customer_ite_map: Dict[int, List[float]] = {}
    for (cid, _lvl), v in ite_lookup.items():
        customer_ite_map.setdefault(cid, []).append(v)

    importances = {r.feature: r.importance for r in feature_importance_repository.list_by_run(db, run_id)}

    customers = customer_repository.list_by_dataset(db, run.dataset_id)
    df = customer_repository.to_dataframe(customers)
    df_clean = cleaning.clean(df)
    feature_set = features.engineer(df_clean)
    means = feature_set.X.mean()
    stds = feature_set.X.std().replace(0, 1.0)
    baseline_outcome_rate = float(feature_set.Y.mean()) if len(feature_set.Y) else 0.0

    refutations = refutation_repository.list_by_run(db, run_id)
    pass_rate = (sum(1 for r in refutations if r.passed) / len(refutations)) if refutations else 0.75

    propensity_diagnostics = propensity_diagnostic_repository.list_by_run(db, run_id)
    propensity_metrics = _extract_propensity_metrics(propensity_diagnostics)

    distinct_treatments = len({s.discount_level for s in ite_scores})
    n_samples = len(ite_scores)

    if "customer_id" in df_clean.columns:
        id_to_index = dict(zip(df_clean["customer_id"], df_clean.index))
    else:
        id_to_index = {cid: idx for idx, cid in enumerate(df_clean.index)}

    items: List[RecommendationItemSchema] = []
    for a in allocations:
        treatment_effect = ite_lookup.get((a.customer_id, a.chosen_discount), 0.0)

        contributing_factors: List[ContributingFactorSchema] = []
        idx = id_to_index.get(a.customer_id)
        if idx is not None and idx in feature_set.X.index:
            row = feature_set.X.loc[idx]
            top_factors = explainability.top_contributing_factors(row, means, stds, importances, top_n=3)
            contributing_factors = [ContributingFactorSchema(**f) for f in top_factors]

        chosen_ci = ci_lookup.get((a.customer_id, a.chosen_discount))
        ci_lower = chosen_ci[0] if chosen_ci else None
        ci_upper = chosen_ci[1] if chosen_ci else None
        customer_ite_values = customer_ite_map.get(a.customer_id, [])
        confidence_result: ConfidenceResult = compute_confidence(
            customer_ite_values,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            chosen_discount=a.chosen_discount,
            refutation_pass_rate=pass_rate,
            n_samples=n_samples,
            n_distinct_treatments=distinct_treatments,
            chosen_ite=treatment_effect,
            pct_outside_support=propensity_metrics["pct_outside_support"],
            pct_extreme=propensity_metrics["pct_extreme"],
            n_unmatched_treated=propensity_metrics["n_unmatched_treated"],
            n_matched_pairs=propensity_metrics["n_matched_pairs"],
        )

        purchase_probability = round(max(0.0, min(1.0, baseline_outcome_rate + treatment_effect)), 3)

        items.append(
            RecommendationItemSchema(
                customer_id=a.customer_id,
                recommended_discount=a.chosen_discount,
                expected_uplift=treatment_effect,
                purchase_probability=purchase_probability,
                confidence_score=confidence_result.confidence_score,
                confidence_level=confidence_result.confidence_level,
                confidence_interval=confidence_result.confidence_interval,
                evidence=confidence_result.evidence,
                contributing_factors=contributing_factors,
            )
        )

    return RecommendationResponseSchema(run_id=run_id, recommendations=items)


def get_recommendations(db: Session, run_id: int) -> RecommendationResponseSchema:
    cached = recommendation_repository.list_by_run(db, run_id)
    if cached:
        items = [
            RecommendationItemSchema(
                customer_id=r.customer_id,
                recommended_discount=r.recommended_discount,
                expected_uplift=r.expected_uplift,
                purchase_probability=r.purchase_probability,
                confidence_score=r.confidence_score,
                confidence_level=r.confidence_level,
                confidence_interval=__import__("json").loads(r.confidence_interval) if r.confidence_interval else None,
                evidence=__import__("json").loads(r.evidence) if r.evidence else None,
                contributing_factors=[
                    ContributingFactorSchema(**f) for f in __import__("json").loads(r.contributing_factors)
                ] if r.contributing_factors else [],
            )
            for r in cached
        ]
        return RecommendationResponseSchema(run_id=run_id, recommendations=items)

    return _compute_recommendations(db, run_id)
