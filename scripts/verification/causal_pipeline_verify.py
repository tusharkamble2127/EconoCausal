"""Complete causal pipeline verification script.

Exercises the full workflow:
  Dataset -> Cleaning -> Feature engineering -> DoWhy causal model ->
  identification -> estimation -> EconML -> ITE -> confidence intervals ->
  refutation -> optimization -> recommendations
"""
from __future__ import annotations

import sys
import os

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

import pandas as pd
import numpy as np

from app.pipeline import cleaning, features, causal_graph, dml_model, optimizer, drift_detector


def generate_synthetic_dataset(n: int = 200) -> pd.DataFrame:
    np.random.seed(42)
    rows = []
    for i in range(n):
        loyalty = np.random.beta(2, 5)
        tenure = np.random.randint(1, 60)
        treatment = float(np.random.choice([0.0, 10.0, 20.0]))
        outcome = int((loyalty + treatment / 100.0 + np.random.normal(0, 0.05)) > 0.5)
        rows.append({
            "customer_id": i + 1,
            "loyalty_score": loyalty,
            "tenure_months": float(tenure),
            "treatment": treatment,
            "outcome": outcome,
        })
    return pd.DataFrame(rows)


def main():
    print("=== Causal Pipeline Verification ===\n")

    # 1. Dataset
    print("[1] Generating synthetic dataset...")
    df = generate_synthetic_dataset(200)
    print(f"    Dataset shape: {df.shape}")

    # 2. Cleaning
    print("[2] Cleaning dataset...")
    df_clean = cleaning.clean(df)
    print(f"    Cleaned shape: {df_clean.shape}")

    # 3. Feature engineering
    print("[3] Engineering features...")
    feature_set = features.engineer(df_clean)
    print(f"    Confounders: {feature_set.X.shape[1]}, Samples: {len(feature_set.T)}")

    # 4. DoWhy causal model
    print("[4] Building DoWhy causal model...")
    model = causal_graph.build_model(df_clean, feature_set.feature_names)
    print("    CausalModel built")

    # 5. Identification
    print("[5] Identifying causal estimand...")
    identified_estimand, estimate = causal_graph.identify_and_estimate(model)
    print(f"    Identified estimand: {identified_estimand.estimand_type}")
    print(f"    DoWhy baseline estimate: {float(estimate.value):.4f}")

    # 6. Refutation
    print("[6] Running refutation tests...")
    refutation_results = causal_graph.run_refutation_tests(model, identified_estimand, estimate)
    for r in refutation_results:
        print(f"    {r.test_name}: passed={r.passed}, new_effect={r.details.get('new_effect', 'N/A')}")

    # 7. EconML
    print("[7] Training EconML LinearDML...")
    est = dml_model.train(feature_set, base_estimator="RandomForest")
    print("    LinearDML trained")

    # 8. ITE + confidence intervals
    print("[8] Estimating ITE with confidence intervals...")
    # Use the first 50 customers, matching X rows to customer_ids
    customer_ids = df_clean["customer_id"].tolist()[:50]
    feature_set_subset = features.FeatureSet(
        X=feature_set.X.iloc[:50],
        T=feature_set.T[:50],
        Y=feature_set.Y[:50],
        feature_names=feature_set.feature_names,
    )
    discount_levels = [0.0, 10.0, 20.0]
    predictions = dml_model.estimate_ite(est, feature_set_subset, customer_ids, discount_levels, ci_alpha=0.1)
    print(f"    Predictions generated: {len(predictions)}")

    # Verify CI shape
    ci_count = sum(1 for p in predictions if p.ci_lower != p.ci_upper)
    print(f"    Predictions with non-degenerate CI: {ci_count}/{len(predictions)}")

    # 9. Optimization
    print("[9] Running budget optimization...")
    ite_matrix = {}
    for p in predictions:
        cid = p.customer_id
        level = p.discount_level
        if cid not in ite_matrix:
            ite_matrix[cid] = {}
        ite_matrix[cid][level] = p.ite_value

    allocations, total_used = optimizer.allocate(ite_matrix, budget=200.0)
    print(f"    Budget used: {total_used:.2f}, Customers targeted: {sum(1 for a in allocations if a.chosen_discount > 0)}")

    # 10. Drift detection
    print("[10] Running drift detection...")
    training_X = feature_set.X
    incoming_X = feature_set.X.sample(frac=0.5, random_state=123)
    drift_reports = drift_detector.detect_drift(training_X, incoming_X)
    drifted_count = sum(1 for r in drift_reports if r.drifted)
    print(f"    Drifted features: {drifted_count}/{len(drift_reports)}")

    print("\n=== CAUSAL PIPELINE VERIFICATION COMPLETE ===")


if __name__ == "__main__":
    main()
