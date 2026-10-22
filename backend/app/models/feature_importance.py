"""Global feature-importance scores for a run, used by the Explainability
panel and to derive per-customer contributing factors on demand."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FeatureImportance(Base):
    __tablename__ = "feature_importances"

    feature_importance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.run_id"), index=True)
    feature: Mapped[str] = mapped_column(String, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)

    run = relationship("Run", back_populates="feature_importances")
