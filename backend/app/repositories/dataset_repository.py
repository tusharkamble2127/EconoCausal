"""Data access for the datasets table (Volume II Chapter 2.2 -- the only
layer allowed to run ORM queries against SQLite)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.dataset import Dataset


def create(db: Session, name: str, row_count: int, owner_id: int) -> Dataset:
    dataset = Dataset(
        name=name,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        row_count=row_count,
        owner_id=owner_id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def get(db: Session, dataset_id: int) -> Optional[Dataset]:
    return db.get(Dataset, dataset_id)


def get_owned(db: Session, dataset_id: int, owner_id: int) -> Optional[Dataset]:
    stmt = select(Dataset).where(Dataset.dataset_id == dataset_id, Dataset.owner_id == owner_id)
    return db.execute(stmt).scalars().first()


def list_by_owner(db: Session, owner_id: int) -> List[Dataset]:
    stmt = select(Dataset).where(Dataset.owner_id == owner_id).order_by(Dataset.dataset_id.desc())
    return list(db.execute(stmt).scalars().all())
