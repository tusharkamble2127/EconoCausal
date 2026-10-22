"""Generate a ~1500-observation synthetic campaign dataset for performance testing."""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd


def generate(n: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    tenure_months = rng.integers(1, 60, size=n).astype(float)
    past_purchase_frequency = rng.poisson(3, size=n).astype(float)
    loyalty_score = rng.uniform(0, 1, size=n)
    avg_order_value = rng.normal(50, 15, size=n).clip(min=5)

    levels = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    treatment = rng.choice(levels, size=n, p=[0.20, 0.15, 0.15, 0.10, 0.10, 0.10, 0.20])

    true_effect_per_dollar = 0.004 + 0.01 * (1 - loyalty_score)
    base_purchase_logit = (
        -1.5
        + 0.02 * tenure_months
        + 0.15 * past_purchase_frequency
        + 1.2 * loyalty_score
        + treatment * true_effect_per_dollar
    )
    purchase_prob = 1 / (1 + np.exp(-base_purchase_logit))
    outcome = rng.binomial(1, purchase_prob)

    df = pd.DataFrame(
        {
            "customer_id": np.arange(1, n + 1),
            "tenure_months": tenure_months,
            "past_purchase_frequency": past_purchase_frequency,
            "loyalty_score": loyalty_score,
            "avg_order_value": avg_order_value,
            "treatment": treatment,
            "outcome": outcome,
        }
    )
    return df



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="D:/roopank/internship/infotact/EconoCausal_Fixed/econocausal/data/raw/perf_test_1500.csv")
    args = parser.parse_args()

    data = generate(args.n, args.seed)
    data.to_csv(args.out, index=False)
    print(f"Wrote {len(data)} rows to {args.out}")
    print("Treatment value counts:")
    print(data["treatment"].value_counts().sort_index())
