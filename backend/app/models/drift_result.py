"""Per-feature data drift results for a run, computed against the most
recent prior completed run's dataset (if any)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DriftResult(Base):
    __tablename__ = "drift_results"

    drift_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    feature: Mapped[str] = mapped_column(String, nullable=False)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)
    drifted: Mapped[int] = mapped_column(Integer, nullable=False)  # 0/1

    run = relationship("Run", back_populates="drift_results")
