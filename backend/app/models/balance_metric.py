"""Balance metric table -- per-feature standardized mean differences."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BalanceMetric(Base):
    __tablename__ = "balance_metrics"

    balance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    feature: Mapped[str] = mapped_column(String, nullable=False)
    smd_before: Mapped[float] = mapped_column(Float, nullable=False)
    smd_after: Mapped[float] = mapped_column(Float, nullable=True)
    improvement: Mapped[float] = mapped_column(Float, nullable=True)
    balanced_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balanced_after: Mapped[int] = mapped_column(Integer, nullable=True)
    match_type: Mapped[str] = mapped_column(String, nullable=False)

    run = relationship("Run", back_populates="balance_metrics")
