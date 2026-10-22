"""Stage 4: diagnose WHY the estimated ATE is near zero."""
from __future__ import annotations
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from scipy.special import expit
from app.pipeline import cleaning, features, dml_model
import generate_mock_data as gmd

df = gmd.generate(n=2000, seed=42)
clean = cleaning.clean(df.copy())
fs = features.engineer(clean)
print("X columns:", list(fs.X.columns))
print("T range:", fs.T.min(), fs.T.max(), "mean", fs.T.mean())
print("Y mean:", fs.Y.mean(), "Y sum:", fs.Y.sum())

est = dml_model.train(fs, "RandomForest")
X = fs.X.to_numpy()
theta_hat = np.asarray(est.const_marginal_effect(X), dtype=float).reshape(-1)
print("theta_hat (per $1): mean", theta_hat.mean(), "std", theta_hat.std())
print("theta_hat * 10 mean:", (theta_hat*10).mean())

eff10 = np.asarray(est.effect(X, T0=np.zeros(len(X)), T1=np.full(len(X), 10.0)), dtype=float).reshape(-1)
print("direct effect@10 mean:", eff10.mean(), "std:", eff10.std())

loyalty = clean["loyalty_score"].to_numpy()
true_theta = 0.004 + 0.01*(1.0-loyalty)
print("true theta mean:", true_theta.mean(), "true theta*10 mean:", (true_theta*10).mean())

from sklearn.ensemble import RandomForestRegressor
rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
rf.fit(X, fs.Y)
pred_y = rf.predict(X)
print("RF Y pred mean:", pred_y.mean(), "corr with Y:", np.corrcoef(pred_y, fs.Y)[0,1])

rft = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
rft.fit(X, fs.T)
pred_t = rft.predict(X)
print("RF T pred mean:", pred_t.mean(), "corr with T:", np.corrcoef(pred_t, fs.T)[0,1])
print("T actual mean:", fs.T.mean())
print("STAGE4 DONE")