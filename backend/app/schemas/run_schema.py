"""Request/response models for the /runs endpoints (Volume II Chapter 7.2-7.3)."""
from __future__ import annotations

import math
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RunCreateSchema(BaseModel):
    dataset_id: int = Field(..., gt=0, description="ID of the uploaded dataset to train on.")
    budget: float = Field(..., ge=0, description="Total discount budget available to allocate.")
    base_estimator: str = Field(default="RandomForest", description="Base estimator for EconML's Double ML.")

    # Campaign configuration page additions (Enhancement #2 and #3). All
    # optional with backward-compatible defaults so existing callers keep
    # working unchanged.
    campaign_name: str = Field(default="Untitled Campaign")
    discount_levels: Optional[List[float]] = Field(
        default_factory=lambda: [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0],
        description="Candidate discount levels (percentages) to evaluate. Must include 0. Defaults to [0, 5, 10, 15, 20, 25, 30].",
    )
    treatment_column: str = Field(default="treatment")
    outcome_column: str = Field(default="outcome")

    @field_validator("budget")
    @classmethod
    def validate_budget_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Budget must be a finite number.")
        return v

    @field_validator("base_estimator")
    @classmethod
    def validate_estimator(cls, v: str) -> str:
        supported = {"RandomForest"}
        if v not in supported:
            raise ValueError(f"Unsupported base_estimator '{v}'. Supported: {sorted(supported)}")
        return v

    @field_validator("discount_levels")
    @classmethod
    def validate_discount_levels(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if not v:
            raise ValueError("discount_levels must not be empty.")
        if len(v) < 2:
            raise ValueError("discount_levels must contain at least two levels for treatment variation.")
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

    @field_validator("treatment_column", "outcome_column")
    @classmethod
    def validate_column_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Column name must not be empty.")
        return v

    @field_validator("campaign_name")
    @classmethod
    def validate_campaign_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return "Untitled Campaign"
        return v


class RunResponseSchema(BaseModel):
    run_id: int
    status: str
    started_at: str
    base_estimator: str
    campaign_name: str = "Untitled Campaign"
    budget: float = 0.0
    discount_levels: List[float] = Field(default_factory=lambda: [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0])
