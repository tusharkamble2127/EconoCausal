"""Request/response models for the /runs/{run_id}/allocation endpoint
(Volume II Chapter 7.5)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class AllocationItemSchema(BaseModel):
    customer_id: int
    chosen_discount: float
    budget_used: float


class AllocationResponseSchema(BaseModel):
    run_id: int
    budget: float
    allocations: List[AllocationItemSchema]
    total_budget_used: float
