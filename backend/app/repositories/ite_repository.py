"""Data access for the ite_scores table."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ite_score import IteScore
from app.pipeline.dml_model import ItePrediction


def bulk_create(db: Session, run_id: int, predictions: List[ItePrediction]) -> None:
    rows = [
        IteScore(
            run_id=run_id,
            customer_id=p.customer_id,
            discount_level=p.discount_level,
            ite_value=p.ite_value,
            ci_lower=p.ci_lower,
            ci_upper=p.ci_upper,
        )
        for p in predictions
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[IteScore]:
    stmt = select(IteScore).where(IteScore.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
