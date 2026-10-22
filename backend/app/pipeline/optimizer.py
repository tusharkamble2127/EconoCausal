"""
Budget-constrained discount allocation optimizer
(Volume I Chapter 8.7, Volume II Chapter 12 Days 15-17 and 20).

Owned by Member 2 (ML & Optimization Engineer, Volume II Chapter 4.2).

Formulation (Volume II Chapter 12, Day 15):
    Decision variables: x[i, k] in {0, 1} -- whether customer i receives
    discount level k (including a $0 "no discount" level).
    Objective: maximize sum_i sum_k ite[i, k] * x[i, k]   (ITE-weighted
    uplift -- NEVER raw predicted purchase probability; see Volume I
    Chapter 9 Week 3 Common Mistakes).
    Constraints:
        sum_k x[i, k] == 1                for every customer i
                                           (exactly one discount level chosen)
        sum_i sum_k cost[k] * x[i, k] <= budget
    This is a linear Mixed-Integer Program, solved with scipy.optimize.milp.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import LinearConstraint, Bounds, milp
from scipy.sparse import csr_matrix

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AllocationResult:
    customer_id: int
    chosen_discount: float
    budget_used: float
    ite_value: float


def allocate(
    ite_matrix: Dict[int, Dict[float, float]],
    budget: float,
) -> Tuple[List[AllocationResult], float]:
    """Solve the budget-constrained allocation problem.

    Args:
        ite_matrix: {customer_id: {discount_level: ite_value}}. Must
            include a 0.0 discount level for every customer (the "no
            discount" option), so the optimizer always has a feasible
            zero-cost choice.
        budget: total dollars available to spend on discounts.

    Returns:
        (list of AllocationResult, total_budget_used)
    """
    customer_ids = sorted(ite_matrix.keys())
    n_customers = len(customer_ids)
    if n_customers == 0:
        return [], 0.0

    discount_levels = sorted(next(iter(ite_matrix.values())).keys())
    n_levels = len(discount_levels)

    # Handle the zero-budget edge case explicitly (Volume II Chapter 12,
    # Day 20) rather than relying on the solver to discover it.
    if budget <= 0:
        logger.info("Budget is zero or negative; allocating no discounts.")
        results = [
            AllocationResult(cid, 0.0, 0.0, ite_matrix[cid].get(0.0, 0.0)) for cid in customer_ids
        ]
        return results, 0.0

    n_vars = n_customers * n_levels

    # Objective: minimize the negative of ITE-weighted uplift (milp minimizes).
    c = np.empty(n_vars, dtype=float)
    for i, cid in enumerate(customer_ids):
        start = i * n_levels
        end = start + n_levels
        c[start:end] = -np.array([ite_matrix[cid].get(level, 0.0) for level in discount_levels], dtype=float)

    # Constraint 1: exactly one discount level per customer.
    row_indices = np.repeat(np.arange(n_customers, dtype=int), n_levels)
    col_indices = np.arange(n_vars, dtype=int)
    A_assign = csr_matrix((np.ones(n_vars, dtype=float), (row_indices, col_indices)), shape=(n_customers, n_vars))
    assign_constraint = LinearConstraint(A_assign, lb=1.0, ub=1.0)

    # Constraint 2: total budget used <= budget.
    budget_row = np.tile(np.array(discount_levels, dtype=float), n_customers)
    budget_constraint = LinearConstraint(budget_row.reshape(1, -1), lb=0.0, ub=budget)

    bounds = Bounds(lb=0, ub=1)
    integrality = np.ones(n_vars)  # all variables binary

    logger.info("Optimizer started: %d customers, %d discount levels, budget=%.2f", n_customers, n_levels, budget)
    result = milp(
        c=c,
        constraints=[assign_constraint, budget_constraint],
        bounds=bounds,
        integrality=integrality,
    )

    if not result.success:
        logger.error("Optimizer failed to find a feasible solution: %s", result.message)
        results = [
            AllocationResult(cid, 0.0, 0.0, ite_matrix[cid].get(0.0, 0.0)) for cid in customer_ids
        ]
        return results, 0.0

    x = result.x.reshape(n_customers, n_levels)
    levels_arr = np.array(discount_levels, dtype=float)
    chosen_indices = np.argmax(x, axis=1)
    results: List[AllocationResult] = []
    total_used = 0.0
    for i, cid in enumerate(customer_ids):
        level = float(levels_arr[chosen_indices[i]])
        results.append(AllocationResult(cid, level, level, ite_matrix[cid].get(level, 0.0)))
        total_used += level

    logger.info("Optimizer completed: total_budget_used=%.2f", total_used)
    return results, total_used
