"""GET /runs/{run_id}/ite (Volume II Chapter 7.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.ite_schema import IteResponseSchema
from app.services import ite_service

router = APIRouter(tags=["ite"])


@router.get("/runs/{run_id}/ite", response_model=IteResponseSchema)
def get_ite(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve Individual Treatment Effect scores for a completed run."""
    return ite_service.get_ite_scores(db, run_id)
