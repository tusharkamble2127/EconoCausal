"""Explainability panel data (Enhancement #7)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FeatureImportanceItemSchema(BaseModel):
    feature: str
    importance: float


class ContributingFactorSchema(BaseModel):
    feature: str
    value: float
    impact: float  # signed contribution estimate


class ExplainabilitySchema(BaseModel):
    run_id: int
    global_feature_importance: List[FeatureImportanceItemSchema]


class CustomerExplanationSchema(BaseModel):
    run_id: int
    customer_id: int
    chosen_discount: float
    estimated_treatment_effect: float
    purchase_probability: float
    confidence_score: float = Field(description="Reliability index in [0, 1] reflecting statistical uncertainty, model stability, data support, and robustness. NOT a probability of correctness.")
    confidence_level: str = Field(default="Insufficient Evidence", description="High, Moderate, Low, or Insufficient Evidence.")
    confidence_interval: Optional[dict] = Field(default=None, description="Estimator confidence interval {lower, upper, level} when available.")
    evidence: Optional[dict] = Field(default=None, description="Supporting evidence flags and metrics.")
    expected_roi: float
    contributing_factors: List[ContributingFactorSchema]
