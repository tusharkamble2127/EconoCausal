"""Recommendation result table -- persisted precomputed recommendation panel."""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecommendationResult(Base):
    __tablename__ = "recommendation_results"

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), index=True, nullable=False)
    recommended_discount: Mapped[float] = mapped_column(Float, nullable=False)
    expected_uplift: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String, nullable=False, default="Insufficient Evidence")
    confidence_interval: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contributing_factors: Mapped[Optional[str]] = mapped_column(String, nullable=True)
