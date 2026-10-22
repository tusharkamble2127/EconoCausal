"""Quick smoke test: does the production pipeline run end-to-end?"""
from __future__ import annotations
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import allocation, balance_metric, customer, dataset, drift_result, feature_importance, ite_score, propensity_diagnostic, propensity_score, recommendation_result, refutation_result, run, password_reset_token, user
from app.models.base import Base
from app.repositories import customer_repository, dataset_repository
from app.schemas.run_schema import RunCreateSchema
from app.services import training_service
sys.path.insert(0, str(ROOT / "data" / "generators"))
import generate_mock_data

# Build in-memory DB
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine)
db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

# Generate data
df = generate_mock_data.generate(n=2000, seed=42)
print("Generated data shape:", df.shape)
print("Treatment values:", sorted(df["treatment"].unique()))
print("Outcome mean:", df["outcome"].mean())

# Insert
feature_cols = [c for c in df.columns if c not in {"treatment", "outcome", "customer_id"}]
rows = []
for _, row in df.iterrows():
    rows.append({
        "features": {c: float(row[c]) for c in feature_cols},
        "treatment": float(row["treatment"]),
        "outcome": int(row["outcome"]),
    })
ds = dataset_repository.create(db, name="smoke", row_count=len(rows), owner_id=1)
customer_repository.bulk_create(db, ds.dataset_id, rows)
print("Inserted dataset", ds.dataset_id)

# Run pipeline
payload = RunCreateSchema(
    dataset_id=ds.dataset_id,
    budget=30000.0,
    base_estimator="RandomForest",
    campaign_name="smoke",
    discount_levels=[0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0],
    treatment_column="treatment",
    outcome_column="outcome",
)
resp = training_service.create_run(db, payload, owner_id=1)
print("Run response:", resp)

# Count ITE rows
ite_rows = db.query(ite_score.IteScore).filter_by(run_id=resp.run_id).all()
print("ITE rows:", len(ite_rows))
for r in ite_rows[:5]:
    print("  ", r.customer_id, r.discount_level, r.ite_value, r.ci_lower, r.ci_upper)

# Check refutations
ref_rows = db.query(refutation_result.RefutationResult).filter_by(run_id=resp.run_id).all()
print("Refutations:", len(ref_rows))
for r in ref_rows:
    print("  ", r.test_name, r.passed)

# Check recommendations
rec_rows = db.query(recommendation_result.RecommendationResult).filter_by(run_id=resp.run_id).all()
print("Recommendations:", len(rec_rows))
for r in rec_rows[:5]:
    print("  cust", r.customer_id, "disc", r.recommended_discount, "conf", r.confidence_score, r.confidence_level)

print("SMOKE TEST PASSED")