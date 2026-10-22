"""Data access for the customers table."""
from __future__ import annotations

import json
from typing import List

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def bulk_create(db: Session, dataset_id: int, rows: List[dict]) -> List[Customer]:
    customers = [
        Customer(
            dataset_id=dataset_id,
            features_json=json.dumps(row["features"]),
            treatment=row["treatment"],
            outcome=row["outcome"],
        )
        for row in rows
    ]
    db.add_all(customers)
    db.commit()
    for c in customers:
        db.refresh(c)
    return customers


def list_by_dataset(db: Session, dataset_id: int) -> List[Customer]:
    stmt = select(Customer).where(Customer.dataset_id == dataset_id)
    return list(db.execute(stmt).scalars().all())


def to_dataframe(customers: List[Customer]) -> pd.DataFrame:
    """Reconstruct a flat DataFrame (features + treatment + outcome + id)
    from Customer ORM rows, for use by the ML pipeline."""
    records = []
    for c in customers:
        record = json.loads(c.features_json)
        record["treatment"] = c.treatment
        record["outcome"] = c.outcome
        if "customer_id" not in record:
            record["customer_id"] = c.customer_id
        records.append(record)
    return pd.DataFrame(records)
