"""Data access for the feature_importances table."""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feature_importance import FeatureImportance


def bulk_create(db: Session, run_id: int, importances: Dict[str, float]) -> None:
    rows = [FeatureImportance(run_id=run_id, feature=f, importance=float(v)) for f, v in importances.items()]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[FeatureImportance]:
    stmt = select(FeatureImportance).where(FeatureImportance.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
