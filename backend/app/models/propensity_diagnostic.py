"""Propensity diagnostic summary table -- stores overlap and summary metrics."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PropensityDiagnostic(Base):
    __tablename__ = "propensity_diagnostics"

    diagnostic_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    details_json: Mapped[str] = mapped_column(String, nullable=False, default="{}")

    run = relationship("Run", back_populates="propensity_diagnostics")
