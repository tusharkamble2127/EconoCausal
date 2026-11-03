"""GET /campaigns (Phase 3 -- campaign history)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.history_schema import CampaignHistorySchema
from app.services import history_service

router = APIRouter(tags=["history"])


@router.get("/campaigns", response_model=CampaignHistorySchema)
def get_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List past campaign runs, scoped to the authenticated caller."""
    return history_service.get_history(db, owner_id=user.user_id)
