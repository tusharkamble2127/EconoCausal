"""Stage 4b: deeper diagnosis of the LinearDML underestimation."""
from __future__ import annotations
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from scipy.special import expit
from sklearn.linear_model import LinearRegression
from app.pipeline import cleaning, features, dml_model
import generate_mock_data as gmd
from econml.dml import LinearDML
from sklearn.ensemble import RandomForestRegressor

df = gmd.generate(n=2000, seed=42)
clean = cleaning.clean(df.copy())
fs = features.engineer(clean)
X = fs.X.to_numpy(); T = fs.T; Y = fs.Y

# Baseline: OLS of Y on T + X
ols = LinearRegression().fit(np.column_stack([T, X]), Y)
print("OLS coef on T:", ols.coef_[0], " (true marginal ~0.0022 per $1, i.e. 0.022 per $10)")

# LinearDML defaults
import inspect
sig = inspect.signature(LinearDML.__init__)
print("LinearDML defaults:")
for k, v in sig.parameters.items():
    if k == "self": continue
    print("  ", k, "=", v.default)

# Try LinearDML with different cv
for cv in [2, 3, 5, 10]:
    est = LinearDML(
        model_y=RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1),
        model_t=RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1),
        discrete_treatment=False,
        random_state=42,
        cv=cv,
    )
    est.fit(Y=Y, T=T, X=X)
    th = np.asarray(est.const_marginal_effect(X), dtype=float).reshape(-1)
    print(f"cv={cv}: theta_hat mean={th.mean():.6f}, effect@10 mean={(th*10).mean():.6f}")

# Try with more trees / deeper
for md in [3, 6, 10]:
    for ne in [100, 500]:
        est = LinearDML(
            model_y=RandomForestRegressor(n_estimators=ne, max_depth=md, random_state=42, n_jobs=-1),
            model_t=RandomForestRegressor(n_estimators=ne, max_depth=md, random_state=42, n_jobs=-1),
            discrete_treatment=False, random_state=42, cv=5,
        )
        est.fit(Y=Y, T=T, X=X)
        th = np.asarray(est.const_marginal_effect(X), dtype=float).reshape(-1)
        print(f"md={md} ne={ne}: theta_hat mean={th.mean():.6f}, effect@10 mean={(th*10).mean():.6f}")

print("STAGE4B DONE")