"""POST /datasets (Volume II Chapter 7.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dataset_schema import DatasetCreateSchema, DatasetResponseSchema
from app.services import dataset_service

router = APIRouter(tags=["datasets"])


@router.post("/datasets", response_model=DatasetResponseSchema, status_code=201)
def create_dataset(payload: DatasetCreateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Register a historical campaign dataset for later training runs."""
    return dataset_service.create_dataset(db, payload, owner_id=user.user_id)
