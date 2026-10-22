"""Customer recommendation panel (Enhancement #6) -- the allocation table,
enriched with expected uplift, purchase probability, confidence, and top
contributing factors for every customer in one response."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.explainability_schema import ContributingFactorSchema


class RecommendationItemSchema(BaseModel):
    customer_id: int
    recommended_discount: float
    expected_uplift: float
    purchase_probability: float
    confidence_score: float = Field(description="Reliability index in [0, 1] reflecting statistical uncertainty, model stability, data support, and robustness. NOT a probability of correctness.")
    confidence_level: str = Field(default="Insufficient Evidence", description="High, Moderate, Low, or Insufficient Evidence.")
    confidence_interval: Optional[dict] = Field(default=None, description="Estimator confidence interval {lower, upper, level} when available.")
    evidence: Optional[dict] = Field(default=None, description="Supporting evidence flags and metrics.")
    contributing_factors: List[ContributingFactorSchema]


class RecommendationResponseSchema(BaseModel):
    run_id: int
    recommendations: List[RecommendationItemSchema]
