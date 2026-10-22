"""Data access for the runs table."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.run import Run


def create(
    db: Session,
    dataset_id: int,
    budget: float,
    base_estimator: str,
    campaign_name: str = "Untitled Campaign",
    discount_levels: Optional[List[float]] = None,
    treatment_column: str = "treatment",
    outcome_column: str = "outcome",
    owner_id: Optional[int] = None,
) -> Run:
    run = Run(
        dataset_id=dataset_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        status="running",
        base_estimator=base_estimator,
        budget=budget,
        campaign_name=campaign_name,
        discount_levels_json=json.dumps(discount_levels or [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]),
        treatment_column=treatment_column,
        outcome_column=outcome_column,
        owner_id=owner_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get(db: Session, run_id: int) -> Optional[Run]:
    return db.get(Run, run_id)


def set_status(db: Session, run: Run, status: str) -> Run:
    run.status = status
    if status in ("complete", "failed"):
        run.completed_at = datetime.now(timezone.utc).isoformat()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_all(db: Session, owner_id: Optional[int] = None) -> List[Run]:
    stmt = select(Run).order_by(Run.run_id.desc())
    if owner_id is not None:
        stmt = stmt.where(Run.owner_id == owner_id)
    return list(db.execute(stmt).scalars().all())


def get_discount_levels(run: Run) -> List[float]:
    return json.loads(run.discount_levels_json)


def most_recent_completed_before(db: Session, run_id: int) -> Optional[Run]:
    """The most recently completed run with a run_id less than the given
    one -- used as the drift-detection reference."""
    stmt = (
        select(Run)
        .where(Run.run_id < run_id, Run.status == "complete")
        .order_by(Run.run_id.desc())
    )
    return db.execute(stmt).scalars().first()
