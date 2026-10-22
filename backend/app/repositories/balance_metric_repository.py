"""Data access for the balance_metrics table."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.balance_metric import BalanceMetric


def bulk_create(db: Session, run_id: int, metrics) -> None:
    rows = [
        BalanceMetric(
            run_id=run_id,
            feature=m.feature,
            smd_before=m.smd_before,
            smd_after=m.smd_after,
            improvement=m.improvement,
            balanced_before=1 if m.balanced_before else 0,
            balanced_after=1 if m.balanced_after else 0,
            match_type=m.match_type,
        )
        for m in metrics
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int):
    stmt = select(BalanceMetric).where(BalanceMetric.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
