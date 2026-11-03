"""Data drift status for the dashboard (Enhancement #9)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import RunNotFoundError
from app.repositories import drift_repository, run_repository
from app.schemas.drift_schema import DriftFeatureSchema, DriftResponseSchema


def get_drift(db: Session, run_id: int) -> DriftResponseSchema:
    run = run_repository.get(db, run_id)
    if run is None:
        raise RunNotFoundError(f"No run with id {run_id}.")

    rows = drift_repository.list_by_run(db, run_id)
    reference_run = run_repository.most_recent_completed_before(db, run_id)

    features = [DriftFeatureSchema(feature=r.feature, p_value=r.p_value, drifted=bool(r.drifted)) for r in rows]
    return DriftResponseSchema(
        run_id=run_id,
        has_reference=reference_run is not None,
        any_drift=any(f.drifted for f in features),
        features=features,
    )
