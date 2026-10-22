"""Stage 6: full multi-seed validation using the EXACT production generator."""
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
DATASETS = [("A", 2000, 42), ("B", 2000, 7), ("C", 2000, 123), ("D", 2000, 456), ("E", 2000, 789), ("F", 1500, 42)]

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

def true_ite_at(df, level):
    loyalty = df["loyalty_score"].to_numpy()
    tenure = df["tenure_months"].to_numpy()
    freq = df["past_purchase_frequency"].to_numpy()
    theta = 0.004 + 0.01 * (1.0 - loyalty)
    eta0 = -1.5 + 0.02 * tenure + 0.15 * freq + 1.2 * loyalty
    p0 = expit(eta0); p1 = expit(eta0 + float(level) * theta)
    return p1 - p0, float(level) * theta

def run_one(db, df, label, dataset_id):
    payload = RunCreateSchema(dataset_id=dataset_id, budget=BUDGET, base_estimator="RandomForest", campaign_name=label, discount_levels=LEVELS, treatment_column="treatment", outcome_column="outcome")
    t0 = time.time()
    resp = training_service.create_run(db, payload, owner_id=1)
    runtime = time.time() - t0
    ite_rows = db.query(ite_score.IteScore).filter_by(run_id=resp.run_id).all()
    ref_rows = db.query(refutation_result.RefutationResult).filter_by(run_id=resp.run_id).all()
    alloc_rows = db.query(allocation.Allocation).filter_by(run_id=resp.run_id).all()
    rec_rows = db.query(recommendation_result.RecommendationResult).filter_by(run_id=resp.run_id).all()
    customers = customer_repository.list_by_dataset(db, dataset_id)
    id_to_row = {c.customer_id: i for i, c in enumerate(sorted(customers, key=lambda c: c.customer_id))}
    pred_records = []
    for r in ite_rows:
        idx = id_to_row[r.customer_id]
        truth_ite, truth_latent = true_ite_at(df, float(r.discount_level))
        pred_records.append({"customer_id": int(r.customer_id), "discount_level": float(r.discount_level), "ite_value": float(r.ite_value), "ci_lower": float(r.ci_lower), "ci_upper": float(r.ci_upper), "true_ite": float(truth_ite[idx]), "true_latent_ite": float(truth_latent[idx])})
    pred_all = pd.DataFrame(pred_records)
    pred_eval = pred_all[abs(pred_all["discount_level"] - EVAL_LEVEL) < 1e-9].copy().reset_index(drop=True)
    refutations = []
    for r in ref_rows:
        details = json.loads(r.details_json) if r.details_json else {}
        refutations.append({"test_name": r.test_name, "passed": bool(r.passed), "original_effect": details.get("original_effect"), "new_effect": details.get("new_effect"), "effect_difference": None if details.get("original_effect") is None or details.get("new_effect") is None else abs(float(details["new_effect"]) - float(details["original_effect"])), "elapsed_s": details.get("elapsed_s"), "is_statistically_significant": details.get("is_statistically_significant")})
    ite_lookup = {(r.customer_id, float(r.discount_level)): (r.ite_value, r.ci_lower, r.ci_upper) for r in ite_rows}
    rec_by_customer = {r.customer_id: r for r in rec_rows}
    confidence_records = []
    for a in alloc_rows:
        rec = rec_by_customer.get(a.customer_id)
        tup = ite_lookup.get((a.customer_id, float(a.chosen_discount)))
        if tup is None or rec is None: continue
        ite_v, ci_lo, ci_hi = tup
        confidence_records.append({"customer_id": int(a.customer_id), "chosen_discount": float(a.chosen_discount), "chosen_ite": float(ite_v), "ci_lower": float(ci_lo), "ci_upper": float(ci_hi), "confidence_score": float(rec.confidence_score), "confidence_level": rec.confidence_level, "evidence": json.loads(rec.evidence) if rec.evidence else {}})
    return {"label": label, "run_id": int(resp.run_id), "status": resp.status, "runtime_s": float(runtime), "n_rows": len(df), "treatment_values": sorted(float(v) for v in df["treatment"].unique()), "outcome_mean": float(df["outcome"].mean()), "prediction_frame": pred_all, "pred_eval_10": pred_eval, "refutations": refutations, "confidence_records": confidence_records, "allocation_count": len(alloc_rows)}

if __name__ == "__main__":
    results = []
    for label, n, seed in DATASETS:
        df = gmd.generate(n=n, seed=seed)
        db = make_db()
        did = insert_dataset(db, df, f"stage6_{label}_{n}_{seed}")
        r = run_one(db, df, label, did)
        results.append(r)
        r["prediction_frame"].to_csv(OUT / f"predictions_{label}.csv", index=False)
        r["pred_eval_10"].to_csv(OUT / f"pred_eval_{label}.csv", index=False)
        pd.DataFrame(r["refutations"]).to_csv(OUT / f"refutations_{label}.csv", index=False)
        pd.DataFrame(r["confidence_records"]).to_csv(OUT / f"confidence_{label}.csv", index=False)
        with open(OUT / f"result_{label}.json", "w") as f:
            json.dump({k: v for k, v in r.items() if not isinstance(v, pd.DataFrame)}, f, indent=2, default=str)
        print(f"{label} n={n} seed={seed} status={r['status']} runtime={r['runtime_s']:.1f}s rows={len(r['pred_eval_10'])}")
    print("STAGE6 DONE")