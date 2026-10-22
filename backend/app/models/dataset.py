"""Dataset table -- Volume I Chapter 6.2.1."""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[str] = mapped_column(String, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    customers = relationship("Customer", back_populates="dataset", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="dataset", cascade="all, delete-orphan")
