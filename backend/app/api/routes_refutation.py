"""GET /runs/{run_id}/refutation (Volume II Chapter 7.6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.ite_schema import RefutationResponseSchema
from app.services import refutation_service

router = APIRouter(tags=["refutation"])


@router.get("/runs/{run_id}/refutation", response_model=RefutationResponseSchema)
def get_refutation(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve DoWhy refutation test results for Mid Review evidence."""
    return refutation_service.get_refutation_results(db, run_id)
