"""Run table -- Volume I Chapter 6.2.3."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.dataset_id"), index=True)
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending/running/complete/failed
    base_estimator: Mapped[str] = mapped_column(String, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Enhancement additions: campaign configuration metadata.
    campaign_name: Mapped[str] = mapped_column(String, nullable=False, default="Untitled Campaign")
    discount_levels_json: Mapped[str] = mapped_column(String, nullable=False, default="[0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]")
    treatment_column: Mapped[str] = mapped_column(String, nullable=False, default="treatment")
    outcome_column: Mapped[str] = mapped_column(String, nullable=False, default="outcome")
    owner_id: Mapped[int] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[str] = mapped_column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="runs")
    ite_scores = relationship("IteScore", back_populates="run", cascade="all, delete-orphan")
    allocations = relationship("Allocation", back_populates="run", cascade="all, delete-orphan")
    refutation_results = relationship("RefutationResult", back_populates="run", cascade="all, delete-orphan")
    drift_results = relationship("DriftResult", back_populates="run", cascade="all, delete-orphan")
    feature_importances = relationship("FeatureImportance", back_populates="run", cascade="all, delete-orphan")
    propensity_scores = relationship("PropensityScore", back_populates="run", cascade="all, delete-orphan")
    propensity_diagnostics = relationship("PropensityDiagnostic", back_populates="run", cascade="all, delete-orphan")
    balance_metrics = relationship("BalanceMetric", back_populates="run", cascade="all, delete-orphan")
