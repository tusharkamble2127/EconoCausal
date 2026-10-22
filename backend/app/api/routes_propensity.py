"""GET /runs/{run_id}/propensity."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.propensity_schema import PropensityResponseSchema
from app.services import propensity_service

router = APIRouter(tags=["propensity"])


@router.get("/runs/{run_id}/propensity", response_model=PropensityResponseSchema)
def get_propensity(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve propensity analysis results for a completed run.

    Returns binary diagnostic propensity (treated vs control) and
    continuous treatment balance diagnostics.
    """
    return propensity_service.get_propensity_results(db, run_id)
