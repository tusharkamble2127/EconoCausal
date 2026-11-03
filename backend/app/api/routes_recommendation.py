"""GET /runs/{run_id}/recommendations (Enhancement #6 -- customer recommendation panel)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.recommendation_schema import RecommendationResponseSchema
from app.services import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/runs/{run_id}/recommendations", response_model=RecommendationResponseSchema)
def get_recommendations(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Enriched per-customer allocation: uplift, purchase probability,
    confidence score, and top contributing factors per customer
    for the recommendation panel."""
    return recommendation_service.get_recommendations(db, run_id)
