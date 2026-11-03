"""
Shared metric computation reused by the summary, analytics, and report
services, so the "causal vs. blanket-targeting baseline" comparison
(Volume I Chapter 8.8) is computed exactly once, consistently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from app.core.config import settings
from app.models.allocation import Allocation
from app.models.ite_score import IteScore


@dataclass
class CampaignMetrics:
    budget: float
    budget_used: float
    customers_total: int
    customers_targeted: int
    average_discount: float
    estimated_uplift: float  # causal, ITE-weighted
    blanket_uplift: float  # naive same-average-discount-for-everyone baseline
    incremental_revenue: float
    blanket_revenue: float
    roi_pct: float
    blanket_roi_pct: float
    roi_improvement_pct: float
    savings_vs_blanket: float
    discount_histogram: Dict[float, int] = field(default_factory=dict)


def compute(budget: float, allocations: List[Allocation], ite_scores: List[IteScore]) -> CampaignMetrics:
    customers_total = len(allocations)
    if customers_total == 0:
        return CampaignMetrics(
            budget=budget,
            budget_used=0.0,
            customers_total=0,
            customers_targeted=0,
            average_discount=0.0,
            estimated_uplift=0.0,
            blanket_uplift=0.0,
            incremental_revenue=0.0,
            blanket_revenue=0.0,
            roi_pct=0.0,
            blanket_roi_pct=0.0,
            roi_improvement_pct=0.0,
            savings_vs_blanket=0.0,
        )

    budget_used = sum(a.budget_used for a in allocations)
    customers_targeted = sum(1 for a in allocations if a.chosen_discount > 0)
    average_discount = (
        sum(a.chosen_discount for a in allocations if a.chosen_discount > 0) / customers_targeted
        if customers_targeted
        else 0.0
    )

    ite_lookup: Dict[tuple, float] = {(s.customer_id, s.discount_level): s.ite_value for s in ite_scores}
    causal_uplift = sum(ite_lookup.get((a.customer_id, a.chosen_discount), 0.0) for a in allocations)

    # Blanket baseline: what if the SAME BUDGET was instead spent giving
    # `customers_targeted` randomly-chosen customers the campaign's average
    # discount, rather than the causally-optimized individualized selection?
    #
    # BUGFIX (forensic pass): the previous version summed the blanket-level
    # ITE across ALL `customers_total` customers, not just
    # `customers_targeted`. That silently compares the real campaign's
    # budget-constrained spend (e.g. $5,000 targeting 25 customers) against
    # an unconstrained hypothetical that gives *every* customer the
    # discount (e.g. $30,000 across all 1,500) -- a ~6x larger implied
    # budget. Because the unconstrained baseline is so much larger, it
    # always looked more profitable in absolute terms, producing a
    # nonsensical negative "savings vs. blanket" even though the causal
    # allocation is, per dollar spent, strictly better (it targets the
    # highest-ITE customers first). Using the *population mean* ITE at the
    # blanket level, scaled by the same `customers_targeted` count, keeps
    # the comparison at the same budget (Enhancement Proposal Section 4).
    blanket_level = round(average_discount, 4)

    def _mean_ite_at_level(level: float) -> float:
        values = [v for (_, lvl), v in ite_lookup.items() if lvl == level]
        return (sum(values) / len(values)) if values else 0.0

    mean_ite_at_blanket_level = _mean_ite_at_level(blanket_level)
    if mean_ite_at_blanket_level == 0.0 and blanket_level not in {level for (_, level) in ite_lookup}:
        # Fall back to the nearest available discount level if the exact
        # average wasn't one of the candidate levels.
        available_levels = sorted({level for (_, level) in ite_lookup})
        if available_levels:
            nearest = min(available_levels, key=lambda lvl: abs(lvl - average_discount))
            mean_ite_at_blanket_level = _mean_ite_at_level(nearest)
    blanket_uplift = mean_ite_at_blanket_level * customers_targeted

    revenue_per_conversion = settings.assumed_revenue_per_conversion
    incremental_revenue = causal_uplift * revenue_per_conversion
    blanket_revenue = blanket_uplift * revenue_per_conversion
    # Same budget-normalization fix: the blanket comparison spends the
    # blanket discount on `customers_targeted` customers, not everyone.
    blanket_budget_used = blanket_level * customers_targeted

    roi_pct = ((incremental_revenue - budget_used) / budget_used * 100) if budget_used > 0 else 0.0
    blanket_roi_pct = (
        ((blanket_revenue - blanket_budget_used) / blanket_budget_used * 100) if blanket_budget_used > 0 else 0.0
    )
    roi_improvement_pct = roi_pct - blanket_roi_pct
    savings_vs_blanket = incremental_revenue - blanket_revenue

    histogram: Dict[float, int] = {}
    for a in allocations:
        histogram[a.chosen_discount] = histogram.get(a.chosen_discount, 0) + 1

    return CampaignMetrics(
        budget=budget,
        budget_used=budget_used,
        customers_total=customers_total,
        customers_targeted=customers_targeted,
        average_discount=average_discount,
        estimated_uplift=causal_uplift,
        blanket_uplift=blanket_uplift,
        incremental_revenue=incremental_revenue,
        blanket_revenue=blanket_revenue,
        roi_pct=roi_pct,
        blanket_roi_pct=blanket_roi_pct,
        roi_improvement_pct=roi_improvement_pct,
        savings_vs_blanket=savings_vs_blanket,
        discount_histogram=histogram,
    )
