"""Explainability panel + per-customer recommendation explanations
(Enhancements #6 and #7)."""
from __future__ import annotations

import json
from typing import Dict

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.pipeline import cleaning, explainability, features
from app.repositories import (
    allocation_repository,
    customer_repository,
    feature_importance_repository,
    ite_repository,
    propensity_diagnostic_repository,
    refutation_repository,
    run_repository,
)
from app.schemas.explainability_schema import (
    ContributingFactorSchema,
    CustomerExplanationSchema,
    ExplainabilitySchema,
    FeatureImportanceItemSchema,
)
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


def get_global_explainability(db: Session, run_id: int) -> ExplainabilitySchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Explainability not available until run {run_id} completes.")

    rows = feature_importance_repository.list_by_run(db, run_id)
    items = sorted(
        (FeatureImportanceItemSchema(feature=r.feature, importance=r.importance) for r in rows),
        key=lambda i: i.importance,
        reverse=True,
    )
    return ExplainabilitySchema(run_id=run_id, global_feature_importance=items)


def get_customer_explanation(db: Session, run_id: int, customer_id: int) -> CustomerExplanationSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Explanations not available until run {run_id} completes.")

    allocations = {a.customer_id: a for a in allocation_repository.list_by_run(db, run_id)}
    allocation = allocations.get(customer_id)
    if allocation is None:
        raise RunNotFoundError(f"No allocation found for customer {customer_id} on run {run_id}.")

    ite_scores = ite_repository.list_by_run(db, run_id)
    ite_lookup = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}
    ci_lookup = {(s.customer_id, s.discount_level): (s.ci_lower, s.ci_upper) for s in ite_scores}
    treatment_effect = ite_lookup.get((customer_id, allocation.chosen_discount), 0.0)

    importances = {r.feature: r.importance for r in feature_importance_repository.list_by_run(db, run_id)}

    customers = customer_repository.list_by_dataset(db, run.dataset_id)
    df = customer_repository.to_dataframe(customers)
    df_clean = cleaning.clean(df)
    feature_set = features.engineer(df_clean)

    contributing_factors = []
    if customer_id in df_clean.get("customer_id", pd.Series(dtype=int)).values:
        idx = df_clean.index[df_clean["customer_id"] == customer_id][0]
        row = feature_set.X.loc[idx]
        means = feature_set.X.mean()
        stds = feature_set.X.std().replace(0, 1.0)
        top_factors = explainability.top_contributing_factors(row, means, stds, importances, top_n=3)
        contributing_factors = [ContributingFactorSchema(**f) for f in top_factors]

    refutations = refutation_repository.list_by_run(db, run_id)
    pass_rate = (sum(1 for r in refutations if r.passed) / len(refutations)) if refutations else 0.75

    propensity_diagnostics = propensity_diagnostic_repository.list_by_run(db, run_id)
    propensity_metrics = _extract_propensity_metrics(propensity_diagnostics)

    ite_scores_all = ite_repository.list_by_run(db, run_id)
    distinct_treatments = len({s.discount_level for s in ite_scores_all})
    n_samples = len(ite_scores_all)

    customer_ite_values = [v for (cid, _lvl), v in ite_lookup.items() if cid == customer_id]
    chosen_ci = ci_lookup.get((customer_id, allocation.chosen_discount))
    ci_lower = chosen_ci[0] if chosen_ci else None
    ci_upper = chosen_ci[1] if chosen_ci else None
    confidence_result: ConfidenceResult = compute_confidence(
        customer_ite_values,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        chosen_discount=allocation.chosen_discount,
        refutation_pass_rate=pass_rate,
        n_samples=n_samples,
        n_distinct_treatments=distinct_treatments,
        chosen_ite=treatment_effect,
        pct_outside_support=propensity_metrics["pct_outside_support"],
        pct_extreme=propensity_metrics["pct_extreme"],
        n_unmatched_treated=propensity_metrics["n_unmatched_treated"],
        n_matched_pairs=propensity_metrics["n_matched_pairs"],
    )

    baseline_outcome_rate = float(feature_set.Y.mean()) if len(feature_set.Y) else 0.0
    purchase_probability = round(max(0.0, min(1.0, baseline_outcome_rate + treatment_effect)), 3)
    expected_roi = (
        (treatment_effect * settings.assumed_revenue_per_conversion - allocation.budget_used)
        / allocation.budget_used
        * 100
        if allocation.budget_used > 0
        else 0.0
    )

    return CustomerExplanationSchema(
        run_id=run_id,
        customer_id=customer_id,
        chosen_discount=allocation.chosen_discount,
        estimated_treatment_effect=treatment_effect,
        purchase_probability=purchase_probability,
        confidence_score=confidence_result.confidence_score,
        confidence_level=confidence_result.confidence_level,
        confidence_interval=confidence_result.confidence_interval,
        evidence=confidence_result.evidence,
        expected_roi=round(expected_roi, 1),
        contributing_factors=contributing_factors,
    )
