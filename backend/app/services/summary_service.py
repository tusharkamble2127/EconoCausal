"""KPI card data for a completed run (Enhancement #4)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import allocation_repository, ite_repository, run_repository
from app.schemas.summary_schema import SummarySchema
from app.services.campaign_metrics import compute


def get_summary(db: Session, run_id: int) -> SummarySchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Summary not available until run {run_id} completes.")

    allocations = allocation_repository.list_by_run(db, run_id)
    ite_scores = ite_repository.list_by_run(db, run_id)
    metrics = compute(run.budget, allocations, ite_scores)

    return SummarySchema(
        run_id=run_id,
        campaign_name=run.campaign_name,
        budget=metrics.budget,
        budget_used=metrics.budget_used,
        budget_utilization_pct=(metrics.budget_used / metrics.budget * 100) if metrics.budget > 0 else 0.0,
        customers_targeted=metrics.customers_targeted,
        customers_total=metrics.customers_total,
        average_discount=metrics.average_discount,
        estimated_uplift=metrics.estimated_uplift,
        roi_improvement_pct=metrics.roi_improvement_pct,
        incremental_revenue=metrics.incremental_revenue,
        savings_vs_blanket=metrics.savings_vs_blanket,
    )
