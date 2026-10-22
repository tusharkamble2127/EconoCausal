"""Business logic for retrieving DoWhy refutation test results
(Volume II Chapter 7.6 -- Mid Review evidence)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotFoundError
from app.repositories import refutation_repository, run_repository
from app.schemas.ite_schema import RefutationResponseSchema, RefutationTestItemSchema


def get_refutation_results(db: Session, run_id: int) -> RefutationResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")

    results = refutation_repository.list_by_run(db, run_id)
    items = [
        RefutationTestItemSchema(test_name=r.test_name, passed=bool(r.passed))
        for r in results
    ]
    return RefutationResponseSchema(run_id=run_id, tests=items)
