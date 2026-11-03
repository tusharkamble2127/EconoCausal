"""Refutation result table -- Volume I Chapter 6.2.6."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefutationResult(Base):
    __tablename__ = "refutation_results"

    refutation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    test_name: Mapped[str] = mapped_column(String, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False)  # 0/1
    details_json: Mapped[str] = mapped_column(String, nullable=False, default="{}")

    run = relationship("Run", back_populates="refutation_results")
