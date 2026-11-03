"""Stage 8: manual ITE verification - compare production wrapper vs direct est.effect."""
from __future__ import annotations
import os, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from app.pipeline import cleaning, features, dml_model
import generate_mock_data as gmd

OUT = ROOT / "artifacts" / "validation"
OUT.mkdir(parents=True, exist_ok=True)
EVAL_LEVEL = 10.0

df = gmd.generate(n=2000, seed=42)
clean = cleaning.clean(df.copy())
fs = features.engineer(clean)
est = dml_model.train(fs, "RandomForest")
X = fs.X.to_numpy()

# Direct effect at 10
direct_10 = np.asarray(est.effect(X, T0=np.zeros(len(X)), T1=np.full(len(X), EVAL_LEVEL)), dtype=float).reshape(-1)
# Structural marginal * 10
struct_10 = np.asarray(est.const_marginal_effect(X), dtype=float).reshape(-1) * EVAL_LEVEL
# Direct effect at 1
direct_1 = np.asarray(est.effect(X, T0=np.zeros(len(X)), T1=np.ones(len(X))), dtype=float).reshape(-1)
struct_1 = np.asarray(est.const_marginal_effect(X), dtype=float).reshape(-1)

# Production wrapper predictions
preds = dml_model.estimate_ite(est, fs, list(range(len(X))), [0.0, EVAL_LEVEL])
prod_10 = np.array([p.ite_value for p in preds if abs(p.discount_level - EVAL_LEVEL) < 1e-9])

print("prod_10 vs direct_10: max_abs_diff =", float(np.max(np.abs(prod_10 - direct_10))))
print("prod_10 vs direct_10: mean_abs_diff =", float(np.mean(np.abs(prod_10 - direct_10))))
print("direct_10 vs struct_10: max_abs_diff =", float(np.max(np.abs(direct_10 - struct_10))))
print("direct_1 vs struct_1: max_abs_diff =", float(np.max(np.abs(direct_1 - struct_1))))
print("prod_10 mean:", prod_10.mean(), "direct_10 mean:", direct_10.mean())
print("struct_10 mean:", struct_10.mean(), "struct_1 mean:", struct_1.mean())

# Manual 20 customers: expected outcome under treatment minus control
from scipy.special import expit
loyalty = clean["loyalty_score"].to_numpy()
tenure = clean["tenure_months"].to_numpy()
freq = clean["past_purchase_frequency"].to_numpy()
theta = 0.004 + 0.01 * (1.0 - loyalty)
eta0 = -1.5 + 0.02 * tenure + 0.15 * freq + 1.2 * loyalty
p0 = expit(eta0)
p1 = expit(eta0 + EVAL_LEVEL * theta)
true_ite = p1 - p0

rng = np.random.default_rng(2026)
selected = rng.choice(len(clean), size=20, replace=False)
manual_rows = []
for idx in selected:
    manual_rows.append({
        "customer_id": int(idx),
        "production_ite_10": float(prod_10[idx]),
        "direct_effect_10": float(direct_10[idx]),
        "structural_marginal_x_10": float(struct_10[idx]),
        "direct_effect_1": float(direct_1[idx]),
        "structural_marginal_x_1": float(struct_1[idx]),
        "true_ite_10": float(true_ite[idx]),
    })
frame = pd.DataFrame(manual_rows)
wrapper_diff = np.abs(frame["production_ite_10"] - frame["direct_effect_10"])
structural_diff = np.abs(frame["direct_effect_10"] - frame["structural_marginal_x_10"])
one_diff = np.abs(frame["direct_effect_1"] - frame["structural_marginal_x_1"])
true_diff = np.abs(frame["production_ite_10"] - frame["true_ite_10"])
print("\nMANUAL ITE (20 customers):")
print("  production vs direct est.effect: max_abs_diff =", float(np.max(wrapper_diff)), "mean_abs_diff =", float(np.mean(wrapper_diff)))
print("  direct vs structural marginal:   max_abs_diff =", float(np.max(structural_diff)), "mean_abs_diff =", float(np.mean(structural_diff)))
print("  unit effect vs structural:       max_abs_diff =", float(np.max(one_diff)))
print("  production vs TRUE ite:          max_abs_diff =", float(np.max(true_diff)), "mean_abs_diff =", float(np.mean(true_diff)))
print("  all wrapper_within_1e-8:", bool(np.all(wrapper_diff < 1e-8)))
print("  all unit_within_1e-8:", bool(np.all(one_diff < 1e-8)))
frame.to_csv(OUT / "manual_ite_20.csv", index=False)
print("STAGE8 DONE")