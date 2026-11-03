"""Data access for the drift_results table."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drift_result import DriftResult
from app.pipeline.drift_detector import DriftReport


def bulk_create(db: Session, run_id: int, reports: List[DriftReport]) -> None:
    rows = [
        DriftResult(run_id=run_id, feature=r.feature, p_value=r.p_value, drifted=1 if r.drifted else 0)
        for r in reports
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[DriftResult]:
    stmt = select(DriftResult).where(DriftResult.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
