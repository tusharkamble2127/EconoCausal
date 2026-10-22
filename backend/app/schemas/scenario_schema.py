"""Scenario simulator request/response (Enhancement #8).

Re-optimizes over already-estimated ITE scores for a completed run under a
hypothetical budget and/or discount-level subset, without retraining.
"""
from __future__ import annotations

import math
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ScenarioRequestSchema(BaseModel):
    budget: float = Field(..., ge=0)
    discount_levels: Optional[List[float]] = Field(
        default=None, description="Subset of the run's original candidate discount levels to allow."
    )

    @field_validator("budget")
    @classmethod
    def validate_budget_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Budget must be a finite number.")
        return v

    @field_validator("discount_levels")
    @classmethod
    def validate_discount_levels(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if not v:
            raise ValueError("discount_levels must not be empty.")
        for level in v:
            if math.isnan(level) or math.isinf(level):
                raise ValueError(f"Discount levels must be finite numbers, got {level}.")
            if level < 0:
                raise ValueError(f"Discount levels must be non-negative, got {level}.")
            if level > 100:
                raise ValueError(f"Discount levels must not exceed 100%, got {level}.")
        if 0.0 not in v:
            raise ValueError("discount_levels must include 0% as the baseline control.")
        if len(set(v)) != len(v):
            raise ValueError("Discount levels must not contain duplicates.")
        return sorted(set(v))


class ScenarioResponseSchema(BaseModel):
    run_id: int
    budget: float
    total_budget_used: float
    customers_targeted: int
    estimated_uplift: float
    average_discount: float

