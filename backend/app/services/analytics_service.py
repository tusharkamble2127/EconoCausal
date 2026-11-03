"""Enhanced visualization data (Enhancement #5).

Retains the existing Uplift/Qini curves (computed client-side from the
existing /ite endpoint) and adds the additional chart data the proposal
asks for: budget allocation by discount, customer segmentation, treatment
distribution, discount distribution, revenue projection, and ROI trend.
"""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import allocation_repository, customer_repository, ite_repository, run_repository
from app.schemas.analytics_schema import AnalyticsSchema, BucketSchema


def get_analytics(db: Session, run_id: int) -> AnalyticsSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Analytics not available until run {run_id} completes.")

    allocations = allocation_repository.list_by_run(db, run_id)
    ite_scores = ite_repository.list_by_run(db, run_id)
    ite_lookup = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}

    # Budget allocation by discount level (dollars spent per level).
    budget_by_level: Dict[float, float] = {}
    discount_counts: Dict[float, int] = {}
    for a in allocations:
        budget_by_level[a.chosen_discount] = budget_by_level.get(a.chosen_discount, 0.0) + a.budget_used
        discount_counts[a.chosen_discount] = discount_counts.get(a.chosen_discount, 0) + 1

    budget_allocation = [
        BucketSchema(label=f"{level:g}%", value=round(val, 2)) for level, val in sorted(budget_by_level.items())
    ]
    discount_distribution = [
        BucketSchema(label=f"{level:g}%", value=count) for level, count in sorted(discount_counts.items())
    ]

    # Historical treatment distribution, straight from the uploaded dataset.
    treatment_distribution: List[BucketSchema] = []
    try:
        customers = customer_repository.list_by_dataset(db, run.dataset_id)
        df = customer_repository.to_dataframe(customers)
        counts = df["treatment"].value_counts().sort_index()
        treatment_distribution = [BucketSchema(label=f"{lvl:g}%", value=int(cnt)) for lvl, cnt in counts.items()]
    except Exception:
        pass

    # Customer segmentation by realized uplift tier (chosen-discount ITE).
    ite_by_customer = {a.customer_id: ite_lookup.get((a.customer_id, a.chosen_discount), 0.0) for a in allocations}
    values = sorted(ite_by_customer.values())
    if values:
        n = len(values)
        low_cut = values[int(n * 0.33)] if n > 2 else values[0]
        high_cut = values[int(n * 0.66)] if n > 2 else values[-1]
    else:
        low_cut = high_cut = 0.0
    segments = {"Low uplift": 0, "Medium uplift": 0, "High uplift": 0}
    for v in ite_by_customer.values():
        if v <= low_cut:
            segments["Low uplift"] += 1
        elif v <= high_cut:
            segments["Medium uplift"] += 1
        else:
            segments["High uplift"] += 1
    customer_segmentation = [BucketSchema(label=k, value=v) for k, v in segments.items()]

    # Revenue projection: cumulative incremental revenue as we target
    # customers in descending order of chosen-discount ITE (mirrors the
    # Uplift curve, in dollar terms).
    ranked = sorted(ite_by_customer.items(), key=lambda kv: kv[1], reverse=True)
    revenue_projection: List[BucketSchema] = []
    running = 0.0
    n = len(ranked) or 1
    for i, (_, v) in enumerate(ranked, start=1):
        running += v * settings.assumed_revenue_per_conversion
        if i % max(1, n // 10) == 0 or i == n:
            pct = round(i / n * 100)
            revenue_projection.append(BucketSchema(label=f"{pct}%", value=round(running, 2)))

    # ROI trend: cumulative ROI% as budget is spent, ranking customers by
    # return-per-dollar (ITE-derived revenue / discount cost) descending.
    roi_ranked = []
    for a in allocations:
        if a.chosen_discount <= 0:
            continue
        revenue = ite_lookup.get((a.customer_id, a.chosen_discount), 0.0) * settings.assumed_revenue_per_conversion
        ratio = revenue / a.budget_used if a.budget_used else 0.0
        roi_ranked.append((ratio, revenue, a.budget_used))
    roi_ranked.sort(key=lambda t: t[0], reverse=True)

    roi_trend: List[BucketSchema] = []
    cum_revenue = 0.0
    cum_cost = 0.0
    m = len(roi_ranked) or 1
    for i, (_, revenue, cost) in enumerate(roi_ranked, start=1):
        cum_revenue += revenue
        cum_cost += cost
        if i % max(1, m // 10) == 0 or i == m:
            pct = round(i / m * 100)
            roi_pct = ((cum_revenue - cum_cost) / cum_cost * 100) if cum_cost > 0 else 0.0
            roi_trend.append(BucketSchema(label=f"{pct}%", value=round(roi_pct, 1)))

    return AnalyticsSchema(
        run_id=run_id,
        budget_allocation_by_discount=budget_allocation,
        treatment_distribution=treatment_distribution,
        discount_distribution=discount_distribution,
        customer_segmentation=customer_segmentation,
        revenue_projection=revenue_projection,
        roi_trend=roi_trend,
    )
