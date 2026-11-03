"""POST /runs and GET /runs/{run_id} (Volume II Chapter 7.2-7.3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_run_ownership
from app.models.user import User
from app.schemas.run_schema import RunCreateSchema, RunResponseSchema
from app.services import training_service

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunResponseSchema, status_code=202)
def create_run(
    payload: RunCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a new causal training + optimization run for a dataset and budget."""
    return training_service.create_run(db, payload, owner_id=user.user_id)


@router.get("/runs/{run_id}", response_model=RunResponseSchema)
def get_run(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Check the status of a training run."""
    return training_service.get_run(db, run_id)
