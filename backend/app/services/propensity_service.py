"""Business logic for retrieving propensity analysis results."""
from __future__ import annotations

import json
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotFoundError, RunNotCompleteError
from app.repositories import propensity_repository, run_repository
from app.schemas.propensity_schema import (
    BalanceMetricSchema,
    BinaryPropensitySchema,
    ContinuousPropensitySchema,
    MatchingResultSchema,
    OverlapDiagnosticSchema,
    PropensityResponseSchema,
)
from app.pipeline.propensity_score import (
    BalanceMetric,
    BinaryPropensityResult,
    ContinuousPropensityResult,
    OverlapDiagnostic,
    PropensityResult,
    MatchingResult,
)


def _schema_from_balance(b: BalanceMetric) -> BalanceMetricSchema:
    return BalanceMetricSchema(
        feature=b.feature,
        smd_before=b.smd_before,
        smd_after=b.smd_after,
        improvement=b.improvement,
        balanced_before=b.balanced_before,
        balanced_after=b.balanced_after,
        match_type=b.match_type,
    )


def get_propensity_results(db: Session, run_id: int) -> PropensityResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Run {run_id} is still in status '{run.status}'.")

    scores = propensity_repository.list_by_run(db, run_id)
    diagnostics = propensity_repository.list_diagnostics_by_run(db, run_id)
    balance_rows = propensity_repository.list_balance_by_run(db, run_id)

    binary = None
    continuous = None
    warnings: List[str] = []

    overlap_data = None
    matching_data = None
    binary_balance: List[BalanceMetric] = []
    continuous_balance: List[BalanceMetric] = []

    for d in diagnostics:
        if d.metric_name == "warning":
            msg = ""
            if d.details_json:
                try:
                    msg = json.loads(d.details_json).get("message", "")
                except Exception:
                    msg = d.details_json
            warnings.append(msg)
        elif d.metric_name == "overlap_summary":
            overlap_data = json.loads(d.details_json)
        elif d.metric_name == "matching_summary":
            matching_data = json.loads(d.details_json)

    for b in balance_rows:
        metric = BalanceMetric(
            feature=b.feature,
            smd_before=b.smd_before,
            smd_after=b.smd_after,
            improvement=b.improvement,
            balanced_before=bool(b.balanced_before),
            balanced_after=bool(b.balanced_after) if b.balanced_after is not None else False,
            match_type=b.match_type,
        )
        if "continuous" in b.match_type:
            continuous_balance.append(metric)
        else:
            binary_balance.append(metric)

    if binary_balance or overlap_data or matching_data or scores:
        propensity_scores = [s.propensity_binary for s in scores]
        binary_schema = BinaryPropensitySchema(
            method="logistic_regression",
            treatment_type="binary_diagnostic",
            sample_size=len(scores),
            propensity_scores=propensity_scores,
            overlap=OverlapDiagnosticSchema(
                min_propensity=overlap_data["min_propensity"] if overlap_data else 0.0,
                max_propensity=overlap_data["max_propensity"] if overlap_data else 0.0,
                common_support_min=overlap_data["common_support_min"] if overlap_data else 0.1,
                common_support_max=overlap_data["common_support_max"] if overlap_data else 0.9,
                n_total=overlap_data["n_total"] if overlap_data else 0,
                n_outside_support=overlap_data["n_outside_support"] if overlap_data else 0,
                pct_outside_support=overlap_data["pct_outside_support"] if overlap_data else 0.0,
                n_extreme_low=overlap_data["n_extreme_low"] if overlap_data else 0,
                n_extreme_high=overlap_data["n_extreme_high"] if overlap_data else 0,
                pct_extreme=overlap_data["pct_extreme"] if overlap_data else 0.0,
            ) if overlap_data else None,
            balance=[_schema_from_balance(b) for b in binary_balance],
            matching=MatchingResultSchema(
                method=matching_data["method"] if matching_data else "nearest_neighbor",
                n_treated=matching_data["n_treated"] if matching_data else 0,
                n_control=matching_data["n_control"] if matching_data else 0,
                n_matched_pairs=matching_data["n_matched_pairs"] if matching_data else 0,
                n_unmatched_treated=matching_data["n_unmatched_treated"] if matching_data else 0,
                n_unmatched_control=matching_data["n_unmatched_control"] if matching_data else 0,
                caliper=matching_data.get("caliper"),
                replacement=matching_data.get("replacement", False),
                matched_treated_indices=matching_data.get("matched_treated_indices") if matching_data else None,
                matched_control_indices=matching_data.get("matched_control_indices") if matching_data else None,
            ) if matching_data else None,
            warnings=warnings,
        )
        binary = binary_schema

    if continuous_balance:
        predicted_continuous = [s.predicted_continuous_treatment for s in scores]
        continuous_schema = ContinuousPropensitySchema(
            method="continuous_stratification",
            treatment_type="continuous",
            sample_size=len(scores),
            predicted_treatment=predicted_continuous,
            n_strata=10,
            balance=[_schema_from_balance(b) for b in continuous_balance],
            warnings=warnings,
        )
        continuous = continuous_schema

    return PropensityResponseSchema(
        run_id=run_id,
        binary=binary,
        continuous=continuous,
        warnings=warnings,
    )
