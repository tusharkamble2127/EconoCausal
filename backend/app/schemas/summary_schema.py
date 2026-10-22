"""KPI summary for a completed run (Enhancement #4)."""
from __future__ import annotations

from pydantic import BaseModel


class SummarySchema(BaseModel):
    run_id: int
    campaign_name: str
    budget: float
    budget_used: float
    budget_utilization_pct: float
    customers_targeted: int
    customers_total: int
    average_discount: float
    estimated_uplift: float
    roi_improvement_pct: float
    incremental_revenue: float
    savings_vs_blanket: float
