"""POST /runs/{run_id}/assistant (Phase 3 -- AI assistant)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.assistant_schema import AssistantRequestSchema, AssistantResponseSchema
from app.services import assistant_service

router = APIRouter(tags=["assistant"])


@router.post("/runs/{run_id}/assistant", response_model=AssistantResponseSchema)
def ask_assistant(run_id: int, payload: AssistantRequestSchema, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Ask the AI assistant to explain this run's recommendations in plain language."""
    return assistant_service.ask(db, run_id, payload)
