"""GET /runs/{run_id}/drift (Enhancement #9 -- data drift detection)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.drift_schema import DriftResponseSchema
from app.services import drift_service

router = APIRouter(tags=["drift"])


@router.get("/runs/{run_id}/drift", response_model=DriftResponseSchema)
def get_drift(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve per-feature data-drift status compared to the previous run."""
    return drift_service.get_drift(db, run_id)
