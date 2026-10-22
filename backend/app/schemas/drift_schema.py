"""Data drift status (Enhancement #9)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class DriftFeatureSchema(BaseModel):
    feature: str
    p_value: float
    drifted: bool


class DriftResponseSchema(BaseModel):
    run_id: int
    has_reference: bool
    any_drift: bool
    features: List[DriftFeatureSchema]
