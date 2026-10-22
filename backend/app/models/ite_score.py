"""ITE score table -- Volume I Chapter 6.2.4.

ci_lower/ci_upper added during the forensic debugging pass: the
Customer Recommendation Panel's confidence score (Enhancement #6) needs
a real per-customer uncertainty signal. See app/pipeline/dml_model.py
and app/services/recommendation_service.py for why the previous
dose-spread heuristic was mathematically constant across the whole
dataset for a LinearDML model and had to be replaced.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IteScore(Base):
    __tablename__ = "ite_scores"

    ite_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    discount_level: Mapped[float] = mapped_column(Float, nullable=False)
    ite_value: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    run = relationship("Run", back_populates="ite_scores")
