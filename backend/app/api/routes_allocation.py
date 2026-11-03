"""GET /runs/{run_id}/allocation (Volume II Chapter 7.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_run_ownership
from app.schemas.allocation_schema import AllocationResponseSchema
from app.services import allocation_service

router = APIRouter(tags=["allocation"])


@router.get("/runs/{run_id}/allocation", response_model=AllocationResponseSchema)
def get_allocation(run_id: int, db: Session = Depends(get_db), _: None = Depends(verify_run_ownership)):
    """Retrieve the optimized discount allocation for a completed run."""
    return allocation_service.get_allocation(db, run_id)
