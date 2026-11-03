"""Stage 5: controlled experiment - does the model respond to stronger/weaker treatment effects?"""
from __future__ import annotations
import os, sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "validation"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from scipy.special import expit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import allocation, balance_metric, customer, dataset, drift_result, feature_importance, ite_score, propensity_diagnostic, propensity_score, recommendation_result, refutation_result, run, password_reset_token, user
from app.models.base import Base
from app.repositories import customer_repository, dataset_repository
from app.schemas.run_schema import RunCreateSchema
from app.services import training_service
import generate_mock_data as gmd

LEVELS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
EVAL_LEVEL = 10.0
BUDGET = 30000.0

def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def insert_dataset(db, df, name):
    feature_cols = [c for c in df.columns if c not in {"treatment", "outcome", "customer_id"}]
    rows = []
    for _, row in df.iterrows():
        rows.append({"features": {c: float(row[c]) for c in feature_cols}, "treatment": float(row["treatment"]), "outcome": int(row["outcome"])})
    ds = dataset_repository.create(db, name=name, row_count=len(rows), owner_id=1)
    customer_repository.bulk_create(db, ds.dataset_id, rows)
    return ds.dataset_id

def true_ate(df, level=EVAL_LEVEL):
    loyalty = df["loyalty_score"].to_numpy()
    tenure = df["tenure_months"].to_numpy()
    freq = df["past_purchase_frequency"].to_numpy()
    theta = 0.004 + 0.01 * (1.0 - loyalty)
    eta0 = -1.5 + 0.02 * tenure + 0.15 * freq + 1.2 * loyalty
    p0 = expit(eta0); p1 = expit(eta0 + float(level) * theta)
    return float(np.mean(p1 - p0))

def run_one(db, df, label, dataset_id):
    payload = RunCreateSchema(dataset_id=dataset_id, budget=BUDGET, base_estimator="RandomForest", campaign_name=label, discount_levels=LEVELS, treatment_column="treatment", outcome_column="outcome")
    resp = training_service.create_run(db, payload, owner_id=1)
    ite_rows = db.query(ite_score.IteScore).filter_by(run_id=resp.run_id).all()
    pred_eval = [float(r.ite_value) for r in ite_rows if abs(float(r.discount_level) - EVAL_LEVEL) < 1e-9]
    estimated_ate = float(np.mean(pred_eval)) if pred_eval else 0.0
    return {"label": label, "run_id": int(resp.run_id), "status": resp.status, "n_ite": len(pred_eval), "estimated_ate": estimated_ate, "true_ate": true_ate(df)}

def generate_controlled(n, seed, effect_multiplier=1.0, tenure_shift=0.0, loyalty_shift=0.0):
    rng = np.random.default_rng(seed)
    tenure = rng.integers(1, 60, size=n).astype(float)
    frequency = rng.poisson(3, size=n).astype(float)
    loyalty = rng.uniform(0, 1, size=n).astype(float)
    aov = rng.normal(50, 15, size=n).clip(min=5)
    if tenure_shift: tenure = tenure + tenure_shift
    if loyalty_shift:
        loyalty = loyalty + loyalty_shift
        loyalty = np.clip(loyalty, 0.0, 1.0)
    propensity_logit = -1.0 + 2.0 * loyalty + 0.05 * frequency
    propensity = 1.0 / (1.0 + np.exp(-propensity_logit))
    def probs(p):
        p0 = max(0.1, 1 - p); p20 = max(0.1, p); p10 = max(0.05, 1 - p0 - p20)
        t = p0 + p10 + p20
        return [p0 / t, p10 / t, p20 / t]
    treatment = np.array([rng.choice([0.0, 10.0, 20.0], p=probs(p)) for p in propensity])
    theta = (0.004 + 0.01 * (1.0 - loyalty)) * effect_multiplier
    eta = -1.5 + 0.02 * tenure + 0.15 * frequency + 1.2 * loyalty + treatment * theta
    outcome = rng.binomial(1, expit(eta))
    return pd.DataFrame({"tenure_months": tenure, "past_purchase_frequency": frequency, "loyalty_score": loyalty, "avg_order_value": aov, "treatment": treatment, "outcome": outcome})

if __name__ == "__main__":
    results = []
    for name, mult, ts, ls in [
        ("baseline_1x", 1.0, 0.0, 0.0),
        ("effect_2x", 2.0, 0.0, 0.0),
        ("effect_0.5x", 0.5, 0.0, 0.0),
        ("effect_5x", 5.0, 0.0, 0.0),
        ("effect_0.1x", 0.1, 0.0, 0.0),
        ("loyalty_up", 1.0, 0.0, 0.15),
        ("tenure_up", 1.0, 10.0, 0.0),
    ]:
        db = make_db()
        df = generate_controlled(2000, 42, effect_multiplier=mult, tenure_shift=ts, loyalty_shift=ls)
        did = insert_dataset(db, df, name)
        r = run_one(db, df, name, did)
        results.append(r)
        print(f"{name:15s} true_ate={r['true_ate']:.6f} est_ate={r['estimated_ate']:.6f} status={r['status']}")
    with open(OUT / "controlled_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("STAGE5 DONE")