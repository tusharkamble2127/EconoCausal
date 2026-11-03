"""Data access for the allocations table."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.pipeline.optimizer import AllocationResult


def bulk_create(db: Session, run_id: int, allocations: List[AllocationResult]) -> None:
    rows = [
        Allocation(
            run_id=run_id,
            customer_id=a.customer_id,
            chosen_discount=a.chosen_discount,
            budget_used=a.budget_used,
        )
        for a in allocations
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[Allocation]:
    stmt = select(Allocation).where(Allocation.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
