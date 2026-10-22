"""Data access for the propensity_diagnostics table."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.propensity_diagnostic import PropensityDiagnostic


def bulk_create(db: Session, run_id: int, diagnostics: List[PropensityDiagnostic]) -> None:
    db.add_all(diagnostics)
    db.commit()


def list_by_run(db: Session, run_id: int) -> List[PropensityDiagnostic]:
    stmt = select(PropensityDiagnostic).where(PropensityDiagnostic.run_id == run_id)
    return list(db.execute(stmt).scalars().all())
