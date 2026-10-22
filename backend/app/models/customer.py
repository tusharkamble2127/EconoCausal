"""Customer table -- Volume I Chapter 6.2.2."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.dataset_id"), index=True)
    features_json: Mapped[str] = mapped_column(String, nullable=False)
    treatment: Mapped[float] = mapped_column(Float, nullable=False)
    outcome: Mapped[int] = mapped_column(Integer, nullable=False)

    dataset = relationship("Dataset", back_populates="customers")
