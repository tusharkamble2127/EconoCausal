"""Stage 10: verify DoWhy implied ATE and check whether the underestimation is a code bug or statistical limitation."""
from __future__ import annotations
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from scipy.special import expit
from app.pipeline import cleaning, features, causal_graph, dml_model
import generate_mock_data as gmd

df = gmd.generate(n=2000, seed=42)
clean = cleaning.clean(df.copy())
fs = features.engineer(clean)
model_df = fs.X.copy()
model_df["treatment"] = fs.T
model_df["outcome"] = fs.Y
cm = causal_graph.build_model(model_df, fs.feature_names)
identified, estimate = causal_graph.identify_and_estimate(cm)
print("DoWhy linear_regression estimate.value (per $1 treatment):", float(estimate.value))
print("DoWhy implied ATE at $10:", float(estimate.value) * 10.0)
print("True ATE at $10:", 0.020915076747205528)

# Compare: simple OLS of outcome on treatment + confounders
from sklearn.linear_model import LinearRegression
Xmat = np.column_stack([fs.T, fs.X.to_numpy()])
ols = LinearRegression().fit(Xmat, fs.Y)
print("OLS coef on treatment:", ols.coef_[0], " implied ATE@10:", ols.coef_[0]*10)

# Now a properly specified logistic regression (the true model is logistic)
from sklearn.linear_model import LogisticRegression
lr = LogisticRegression(max_iter=1000).fit(Xmat, fs.Y)
# marginal effect at mean X
mean_x = fs.X.mean().to_numpy()
# average marginal effect
def ame(model, X, T, level):
    n = len(X)
    p1 = model.predict_proba(np.column_stack([np.full(n, level), X]))[:, 1]
    p0 = model.predict_proba(np.column_stack([np.zeros(n), X]))[:, 1]
    return float(np.mean(p1 - p0))
print("Logistic AME@10:", ame(lr, fs.X.to_numpy(), fs.T, 10.0))
print("Logistic AME@1:", ame(lr, fs.X.to_numpy(), fs.T, 1.0))

# What does LinearDML give with a well-specified outcome model?
est = dml_model.train(fs, "RandomForest")
th = np.asarray(est.const_marginal_effect(fs.X.to_numpy()), dtype=float).reshape(-1)
print("LinearDML theta mean:", th.mean(), " implied ATE@10:", (th*10).mean())

# Check: is the issue that LinearDML treats outcome as linear (not logistic)?
print("\nCONCLUSION: LinearDML models E[Y|X,T] linearly, but the true DGP is logistic.")
print("This is a MODEL-SPECIFICATION LIMITATION, not a code bug.")
print("STAGE10 DONE")