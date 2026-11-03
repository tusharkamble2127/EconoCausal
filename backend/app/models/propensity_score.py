"""Propensity score table -- stores per-customer propensity and treatment predictions."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PropensityScore(Base):
    __tablename__ = "propensity_scores"

    propensity_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    propensity_binary: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_continuous_treatment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    in_matched_sample: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_with_customer_id: Mapped[int] = mapped_column(Integer, nullable=True)

    run = relationship("Run", back_populates="propensity_scores")
