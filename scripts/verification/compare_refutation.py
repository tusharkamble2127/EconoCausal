"""Compare original DoWhy refutation with current optimized implementation."""
from __future__ import annotations

import json
import time
import numpy as np
import pandas as pd
import statsmodels.api as sm

from dowhy import CausalModel
from dowhy.causal_refuters import (
    PlaceboTreatmentRefuter,
    RandomCommonCause,
    DataSubsetRefuter,
)

import sys
sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")

from app.pipeline import causal_graph as cg_opt

# Load the same dataset used in benchmark
DATASET_PATH = r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\data\raw\perf_test_1500.csv"

print("Loading dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"Loaded {len(df)} rows")

# Reconstruct the feature set as the pipeline does
from app.pipeline import cleaning, features

df_clean = cleaning.clean(df, treatment_col="treatment", outcome_col="outcome")
cleaning.validate_treatment_variation(df_clean, treatment_col="treatment")
feature_set = features.engineer(df_clean, treatment_col="treatment", outcome_col="outcome")

model_df = feature_set.X.copy()
model_df["treatment"] = feature_set.T
model_df["outcome"] = feature_set.Y

treatment_col = "treatment"
outcome_col = "outcome"
confounders = feature_set.feature_names

# Build DoWhy model
print("Building DoWhy model...")
model = CausalModel(
    data=model_df,
    treatment=treatment_col,
    outcome=outcome_col,
    common_causes=confounders,
)

identified, estimate = cg_opt.identify_and_estimate(model)
print(f"DoWhy baseline estimate: {estimate.value}")

# Original DoWhy refutations
print("\n=== Original DoWhy Refutation ===")

# 1. Placebo treatment
t0 = time.time()
placebo_refuter = PlaceboTreatmentRefuter(
    model._data,
    identified_estimand=identified,
    estimate=estimate,
    num_simulations=100,
    random_state=42,
)
placebo_res = placebo_refuter.refute_estimate(show_progress_bar=False)
placebo_elapsed = time.time() - t0
print(f"placebo_treatment: new_effect={placebo_res.new_effect}, p_value={placebo_res.refutation_result['p_value']}, elapsed={placebo_elapsed:.2f}s")

# 2. Random common cause
t0 = time.time()
random_refuter = RandomCommonCause(
    model._data,
    identified_estimand=identified,
    estimate=estimate,
    num_simulations=100,
    random_state=42,
)
random_res = random_refuter.refute_estimate(show_progress_bar=False)
random_elapsed = time.time() - t0
print(f"random_common_cause: new_effect={random_res.new_effect}, p_value={random_res.refutation_result['p_value']}, elapsed={random_elapsed:.2f}s")

# 3. Data subset
t0 = time.time()
subset_refuter = DataSubsetRefuter(
    model._data,
    identified_estimand=identified,
    estimate=estimate,
    subset_fraction=0.8,
    num_simulations=100,
    random_state=42,
)
subset_res = subset_refuter.refute_estimate(show_progress_bar=False)
subset_elapsed = time.time() - t0
print(f"data_subset: new_effect={subset_res.new_effect}, p_value={subset_res.refutation_result['p_value']}, elapsed={subset_elapsed:.2f}s")

# Current optimized implementation
print("\n=== Current Optimized Implementation ===")
t0 = time.time()
opt_results = cg_opt.run_refutation_tests(model, identified, estimate)
opt_elapsed = time.time() - t0
for r in opt_results:
    print(f"{r.test_name}: passed={r.passed}, details={r.details}, elapsed={r.details.get('elapsed_s', 'N/A')}s")
print(f"Total optimized refutation elapsed: {opt_elapsed:.2f}s")

# Summary
print("\n=== Comparison Summary ===")
print(f"Original placebo p_value: {placebo_res.refutation_result['p_value']:.4f}")
print(f"Original random p_value: {random_res.refutation_result['p_value']:.4f}")
print(f"Original subset p_value: {subset_res.refutation_result['p_value']:.4f}")
print(f"Original total time: {placebo_elapsed + random_elapsed + subset_elapsed:.2f}s")
print(f"Optimized total time: {opt_elapsed:.2f}s")
