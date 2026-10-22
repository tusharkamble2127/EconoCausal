"""Campaign history list (Phase 3)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CampaignHistoryItemSchema(BaseModel):
    run_id: int
    campaign_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    base_estimator: str
    budget: float
    dataset_name: str


class CampaignHistorySchema(BaseModel):
    campaigns: List[CampaignHistoryItemSchema]
