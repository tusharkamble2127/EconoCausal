"""Data access for the refutation_results table."""
from __future__ import annotations

import json
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refutation_result import RefutationResult
from app.pipeline.causal_graph import RefutationOutcome


def bulk_create(db: Session, run_id: int, outcomes: List[RefutationOutcome]) -> None:
    rows = [
        RefutationResult(
            run_id=run_id,
            test_name=o.test_name,
            passed=1 if o.passed else 0,
            details_json=json.dumps(o.details),
        )
        for o in outcomes
    ]
    db.add_all(rows)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[RefutationResult]:
    stmt = select(RefutationResult).where(RefutationResult.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
