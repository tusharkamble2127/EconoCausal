"""Request/response models for the /runs/{run_id}/propensity endpoint."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class OverlapDiagnosticSchema(BaseModel):
    min_propensity: float
    max_propensity: float
    common_support_min: float
    common_support_max: float
    n_total: int
    n_outside_support: int
    pct_outside_support: float
    n_extreme_low: int
    n_extreme_high: int
    pct_extreme: float


class BalanceMetricSchema(BaseModel):
    feature: str
    smd_before: float
    smd_after: Optional[float]
    improvement: Optional[float]
    balanced_before: bool
    balanced_after: bool
    match_type: str


class MatchingResultSchema(BaseModel):
    method: str
    n_treated: int
    n_control: int
    n_matched_pairs: int
    n_unmatched_treated: int
    n_unmatched_control: int
    caliper: Optional[float]
    replacement: bool
    matched_treated_indices: Optional[List[int]] = None
    matched_control_indices: Optional[List[int]] = None


class BinaryPropensitySchema(BaseModel):
    method: str
    treatment_type: str
    sample_size: int
    propensity_scores: List[float]
    overlap: Optional[OverlapDiagnosticSchema]
    balance: List[BalanceMetricSchema]
    matching: Optional[MatchingResultSchema]
    warnings: List[str]


class ContinuousPropensitySchema(BaseModel):
    method: str
    treatment_type: str
    sample_size: int
    predicted_treatment: List[float]
    n_strata: int
    balance: List[BalanceMetricSchema]
    warnings: List[str]


class PropensityResponseSchema(BaseModel):
    run_id: int
    binary: Optional[BinaryPropensitySchema]
    continuous: Optional[ContinuousPropensitySchema]
    warnings: List[str]
