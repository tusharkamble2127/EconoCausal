"""GET /runs/{run_id}/summary (Enhancement #4 -- KPI cards)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.summary_schema import SummarySchema
from app.services import summary_service

router = APIRouter(tags=["summary"])


@router.get("/runs/{run_id}/summary", response_model=SummarySchema)
def get_summary(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve KPI-card metrics for a completed run."""
    return summary_service.get_summary(db, run_id)
