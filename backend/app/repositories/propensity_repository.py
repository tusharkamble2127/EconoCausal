"""Data access for the propensity_scores, propensity_diagnostics, and balance_metrics tables."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.balance_metric import BalanceMetric
from app.models.propensity_diagnostic import PropensityDiagnostic
from app.models.propensity_score import PropensityScore
from app.pipeline.propensity_score import PropensityResult


def bulk_create_scores(
    db: Session,
    run_id: int,
    customer_ids: List[int],
    propensity_scores: List[float],
    predicted_continuous_treatment: List[float],
    matched_indices: List[int],
    matched_pair_map: Optional[Dict[int, int]] = None,
) -> None:
    rows = []
    matched_set = set(matched_indices)
    for i, cid in enumerate(customer_ids):
        matched_customer_id = None
        if matched_pair_map and i in matched_pair_map:
            matched_customer_id = customer_ids[matched_pair_map[i]]
        rows.append(
            PropensityScore(
                run_id=run_id,
                customer_id=cid,
                propensity_binary=float(propensity_scores[i]) if i < len(propensity_scores) else 0.0,
                predicted_continuous_treatment=float(predicted_continuous_treatment[i]) if i < len(predicted_continuous_treatment) else 0.0,
                in_matched_sample=1 if i in matched_set else 0,
                matched_with_customer_id=matched_customer_id,
            )
        )
    db.add_all(rows)
    db.commit()


def bulk_create_diagnostics(
    db: Session,
    run_id: int,
    result: PropensityResult,
) -> None:
    rows: List[PropensityDiagnostic] = []

    if result.binary and result.binary.overlap:
        o = result.binary.overlap
        rows.append(PropensityDiagnostic(
            run_id=run_id,
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
        rows.append(PropensityDiagnostic(
            run_id=run_id,
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
            }),
        ))

    for w in result.warnings:
        rows.append(PropensityDiagnostic(
            run_id=run_id,
            metric_name="warning",
            metric_value=0.0,
            details_json=json.dumps({"message": w}),
        ))

    if rows:
        db.add_all(rows)
        db.commit()


def bulk_create_balance(
    db: Session,
    run_id: int,
    balance_metrics: List,
) -> None:
    rows = [
        BalanceMetric(
            run_id=run_id,
            feature=b.feature,
            smd_before=b.smd_before,
            smd_after=b.smd_after if b.smd_after is not None else None,
            improvement=b.improvement if b.improvement is not None else None,
            balanced_before=1 if b.balanced_before else 0,
            balanced_after=1 if b.balanced_after else 0,
            match_type=b.match_type,
        )
        for b in balance_metrics
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[PropensityScore]:
    stmt = select(PropensityScore).where(PropensityScore.run_id == run_id)
    return list(db.execute(stmt).scalars().all())


def list_diagnostics_by_run(db: Session, run_id: int) -> List[PropensityDiagnostic]:
    stmt = select(PropensityDiagnostic).where(PropensityDiagnostic.run_id == run_id)
    return list(db.execute(stmt).scalars().all())


def list_balance_by_run(db: Session, run_id: int) -> List[BalanceMetric]:
    stmt = select(BalanceMetric).where(BalanceMetric.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
