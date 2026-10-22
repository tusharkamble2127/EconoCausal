"""Enhanced visualization data (Enhancement #5)."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class BucketSchema(BaseModel):
    label: str
    value: float


class AnalyticsSchema(BaseModel):
    run_id: int
    budget_allocation_by_discount: List[BucketSchema]
    treatment_distribution: List[BucketSchema]
    discount_distribution: List[BucketSchema]
    customer_segmentation: List[BucketSchema]
    revenue_projection: List[BucketSchema]
    roi_trend: List[BucketSchema]
