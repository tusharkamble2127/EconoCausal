"""GET /runs/{run_id}/analytics (Enhancement #5 -- enhanced visualizations)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.analytics_schema import AnalyticsSchema
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/runs/{run_id}/analytics", response_model=AnalyticsSchema)
def get_analytics(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve chart data for the enhanced analytics panels."""
    return analytics_service.get_analytics(db, run_id)
