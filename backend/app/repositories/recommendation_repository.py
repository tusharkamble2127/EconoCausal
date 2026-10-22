"""Data access for the recommendation_results table."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation_result import RecommendationResult


def bulk_create(db: Session, results: List[RecommendationResult]) -> None:
    db.add_all(results)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[RecommendationResult]:
    stmt = select(RecommendationResult).where(RecommendationResult.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
