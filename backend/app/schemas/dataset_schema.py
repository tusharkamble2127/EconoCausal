"""Request/response models for the /datasets endpoints (Volume II Chapter 7.1)."""
from __future__ import annotations

import math
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator


class CustomerRowSchema(BaseModel):
    features: Dict[str, float] = Field(..., description="Confounder feature vector for this customer.")
    treatment: float = Field(..., description="Discount amount actually offered historically.")
    outcome: int = Field(..., ge=0, le=1, description="Whether the customer purchased/stayed (0 or 1).")

    @field_validator("features", mode="before")
    @classmethod
    def validate_features_finite(cls, v):
        if isinstance(v, dict):
            for key, val in v.items():
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    raise ValueError(f"Feature '{key}' must be a finite number, got {val}.")
        return v

    @field_validator("treatment", mode="before")
    @classmethod
    def validate_treatment_finite(cls, v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError(f"Treatment must be a finite number, got {v}.")
        return v


class DatasetCreateSchema(BaseModel):
    name: str
    rows: List[CustomerRowSchema]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Dataset name must not be empty.")
        return v

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v: List[CustomerRowSchema]) -> List[CustomerRowSchema]:
        if not v:
            raise ValueError("Dataset must contain at least one row.")
        return v


class DatasetResponseSchema(BaseModel):
    dataset_id: int
    name: str
    row_count: int
    uploaded_at: str
