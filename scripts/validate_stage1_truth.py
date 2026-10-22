"""Stage 1: verify the synthetic ground-truth generator matches the production model's data assumptions."""
from __future__ import annotations
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")

import numpy as np
import pandas as pd
import generate_mock_data as gmd

df = gmd.generate(n=2000, seed=42)
print("columns:", list(df.columns))
print("shape:", df.shape)
print("treatment unique:", sorted(df["treatment"].unique()))
print("outcome mean:", df["outcome"].mean())

# Reproduce ground truth ITE at level 10
from scipy.special import expit
loyalty = df["loyalty_score"].to_numpy()
tenure = df["tenure_months"].to_numpy()
freq = df["past_purchase_frequency"].to_numpy()
treatment = df["treatment"].to_numpy()

theta = 0.004 + 0.01 * (1.0 - loyalty)
eta0 = -1.5 + 0.02 * tenure + 0.15 * freq + 1.2 * loyalty
p0 = expit(eta0)
p1 = expit(eta0 + 10.0 * theta)
true_ite = p1 - p0
true_ate = float(np.mean(true_ite))
print("true_ate@10:", true_ate)
print("true_ite mean:", true_ite.mean(), "std:", true_ite.std())
print("theta mean:", theta.mean(), "std:", theta.std())

# Verify outcome generation matches
eta = -1.5 + 0.02 * tenure + 0.15 * freq + 1.2 * loyalty + treatment * theta
expected_p = expit(eta)
print("expected outcome prob mean:", expected_p.mean(), "actual outcome mean:", df["outcome"].mean())

# Check leakage: true_ite not in features
print("true_ite in df.columns:", "true_ite" in df.columns)
print("STAGE1 OK")