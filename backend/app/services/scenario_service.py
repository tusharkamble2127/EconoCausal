"""Scenario simulator (Enhancement #8).

Re-runs only the budget optimizer over a completed run's already-estimated
ITE scores under a hypothetical budget and/or discount-level subset --
no retraining required, so this responds fast enough for interactive
"what-if" exploration.
"""
from __future__ import annotations

import json
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidDatasetError, RunNotCompleteError, RunNotFoundError
from app.pipeline import optimizer
from app.repositories import ite_repository, run_repository
from app.schemas.scenario_schema import ScenarioRequestSchema, ScenarioResponseSchema


def simulate(db: Session, run_id: int, payload: ScenarioRequestSchema) -> ScenarioResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Scenario simulation not available until run {run_id} completes.")

    original_levels = set(json.loads(run.discount_levels_json))
    requested_levels = set(payload.discount_levels) if payload.discount_levels else original_levels
    invalid = requested_levels - original_levels
    if invalid:
        raise InvalidDatasetError(
            f"Invalid discount levels {sorted(invalid)}. Allowed levels for this run: {sorted(original_levels)}."
        )

    ite_scores = ite_repository.list_by_run(db, run_id)
    allowed_levels = requested_levels

    ite_matrix: dict = {}
    for s in ite_scores:
        if s.discount_level not in allowed_levels and s.discount_level != 0.0:
            continue
        ite_matrix.setdefault(s.customer_id, {})[s.discount_level] = s.ite_value

    # Every customer needs a 0.0 "no discount" fallback option.
    for cid, levels in ite_matrix.items():
        levels.setdefault(0.0, 0.0)

    allocations, total_used = optimizer.allocate(ite_matrix, payload.budget)

    targeted = [a for a in allocations if a.chosen_discount > 0]
    uplift = sum(a.ite_value for a in allocations)
    avg_discount = (sum(a.chosen_discount for a in targeted) / len(targeted)) if targeted else 0.0

    return ScenarioResponseSchema(
        run_id=run_id,
        budget=payload.budget,
        total_budget_used=total_used,
        customers_targeted=len(targeted),
        estimated_uplift=uplift,
        average_discount=avg_discount,
    )
