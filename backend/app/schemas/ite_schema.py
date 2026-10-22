"""Request/response models for the /runs/{run_id}/ite and /refutation endpoints
(Volume II Chapter 7.4 and 7.6)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class IteScoreItemSchema(BaseModel):
    customer_id: int
    discount_level: float
    ite_value: float


class IteResponseSchema(BaseModel):
    run_id: int
    scores: List[IteScoreItemSchema]


class RefutationTestItemSchema(BaseModel):
    test_name: str
    passed: bool


class RefutationResponseSchema(BaseModel):
    run_id: int
    tests: List[RefutationTestItemSchema]
