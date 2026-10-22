"""Business logic for retrieving the optimized allocation (Volume II Chapter 7.5)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import allocation_repository, run_repository
from app.schemas.allocation_schema import AllocationItemSchema, AllocationResponseSchema


def get_allocation(db: Session, run_id: int) -> AllocationResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Allocation not available until run {run_id} completes.")

    allocations = allocation_repository.list_by_run(db, run_id)
    items = [
        AllocationItemSchema(customer_id=a.customer_id, chosen_discount=a.chosen_discount, budget_used=a.budget_used)
        for a in allocations
    ]
    total_used = sum(item.budget_used for item in items)

    return AllocationResponseSchema(
        run_id=run_id, budget=run.budget, allocations=items, total_budget_used=total_used
    )
