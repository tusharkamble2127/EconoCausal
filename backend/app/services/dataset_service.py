"""Business logic for registering datasets (Volume II Chapter 10.1)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import customer_repository, dataset_repository
from app.schemas.dataset_schema import DatasetCreateSchema, DatasetResponseSchema


def create_dataset(db: Session, payload: DatasetCreateSchema, owner_id: int) -> DatasetResponseSchema:
    dataset = dataset_repository.create(db, name=payload.name, row_count=len(payload.rows), owner_id=owner_id)
    rows = [row.model_dump() for row in payload.rows]
    customer_repository.bulk_create(db, dataset.dataset_id, rows)

    return DatasetResponseSchema(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        row_count=dataset.row_count,
        uploaded_at=dataset.uploaded_at,
    )
