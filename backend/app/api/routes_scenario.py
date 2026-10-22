"""POST /runs/{run_id}/simulate (Enhancement #8 -- scenario simulator)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.scenario_schema import ScenarioRequestSchema, ScenarioResponseSchema
from app.services import scenario_service

router = APIRouter(tags=["scenario"])


@router.post("/runs/{run_id}/simulate", response_model=ScenarioResponseSchema)
def simulate(run_id: int, payload: ScenarioRequestSchema, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Simulate a different budget / discount-level subset without retraining."""
    return scenario_service.simulate(db, run_id, payload)
