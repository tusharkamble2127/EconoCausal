"""Business logic for retrieving ITE scores (Volume II Chapter 7.4)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotCompleteError, RunNotFoundError
from app.repositories import ite_repository, run_repository
from app.schemas.ite_schema import IteResponseSchema, IteScoreItemSchema


def get_ite_scores(db: Session, run_id: int) -> IteResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.status != "complete":
        raise RunNotCompleteError(f"Run {run_id} is still in status '{run.status}'.")

    scores = ite_repository.list_by_run(db, run_id)
    items = [
        IteScoreItemSchema(customer_id=s.customer_id, discount_level=s.discount_level, ite_value=s.ite_value)
        for s in scores
    ]
    return IteResponseSchema(run_id=run_id, scores=items)
