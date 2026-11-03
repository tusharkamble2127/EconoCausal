"""Campaign history list (Phase 3)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.repositories import dataset_repository, run_repository
from app.schemas.history_schema import CampaignHistoryItemSchema, CampaignHistorySchema


def get_history(db: Session, owner_id: Optional[int] = None) -> CampaignHistorySchema:
    runs = run_repository.list_all(db, owner_id=owner_id)
    items = []
    for run in runs:
        dataset = dataset_repository.get(db, run.dataset_id)
        items.append(
            CampaignHistoryItemSchema(
                run_id=run.run_id,
                campaign_name=run.campaign_name,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                base_estimator=run.base_estimator,
                budget=run.budget,
                dataset_name=dataset.name if dataset else "Unknown dataset",
            )
        )
    return CampaignHistorySchema(campaigns=items)
