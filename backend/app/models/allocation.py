"""Allocation table -- Volume I Chapter 6.2.5."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    chosen_discount: Mapped[float] = mapped_column(Float, nullable=False)
    budget_used: Mapped[float] = mapped_column(Float, nullable=False)

    run = relationship("Run", back_populates="allocations")
