"""GET /runs/{run_id}/explainability and .../customers/{customer_id}/explanation
(Enhancements #6 and #7)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.explainability_schema import CustomerExplanationSchema, ExplainabilitySchema
from app.services import explainability_service

router = APIRouter(tags=["explainability"])


@router.get("/runs/{run_id}/explainability", response_model=ExplainabilitySchema)
def get_explainability(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Global feature importances for the explainability panel."""
    return explainability_service.get_global_explainability(db, run_id)


@router.get("/runs/{run_id}/customers/{customer_id}/explanation", response_model=CustomerExplanationSchema)
def get_customer_explanation(run_id: int, customer_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Per-customer recommendation explanation: effect, probability,
    confidence, ROI, and top contributing factors."""
    return explainability_service.get_customer_explanation(db, run_id, customer_id)
