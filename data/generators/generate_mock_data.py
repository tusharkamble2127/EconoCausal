"""
Synthetic mock dataset generator (Volume I Chapter 7.1).

Generates a retail/marketing-style dataset with a known, controllable
treatment effect, so the causal pipeline's estimates can be checked
against a known ground truth during development -- recommended for
Week 1 so the team is not blocked waiting for a "real" dataset.

Usage:
    python generators/generate_mock_data.py --n 2000 --out raw/mock_campaign.csv
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Confounders.
    tenure_months = rng.integers(1, 60, size=n).astype(float)
    past_purchase_frequency = rng.poisson(3, size=n).astype(float)
    loyalty_score = rng.uniform(0, 1, size=n)
    avg_order_value = rng.normal(50, 15, size=n).clip(min=5)

    # Propensity to receive a discount depends on confounders (observational,
    # not randomized) -- loyal, frequent customers are historically more
    # likely to have been targeted with discounts.
    propensity_logit = -1.0 + 2.0 * loyalty_score + 0.05 * past_purchase_frequency
    propensity = 1 / (1 + np.exp(-propensity_logit))

    # Historical treatment: 0, 10, or 20 dollar discount, weighted by propensity.
    treatment = np.array(
        [rng.choice([0.0, 10.0, 20.0], p=_treatment_probs(p)) for p in propensity]
    )

    # True (unobservable in reality, known here for validation) treatment
    # effect: higher discount -> higher purchase probability, effect size
    # varies by loyalty ("persuadable" customers respond more).
    true_effect_per_dollar = 0.004 + 0.01 * (1 - loyalty_score)  # less loyal = more persuadable
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
            "tenure_months": tenure_months,
            "past_purchase_frequency": past_purchase_frequency,
            "loyalty_score": loyalty_score,
            "avg_order_value": avg_order_value,
            "treatment": treatment,
            "outcome": outcome,
        }
    )
    return df


def _treatment_probs(p: float):
    # Higher propensity shifts probability mass toward larger discounts.
    p0 = max(0.1, 1 - p)
    p20 = max(0.1, p)
    p10 = max(0.05, 1 - p0 - p20)
    total = p0 + p10 + p20
    return [p0 / total, p10 / total, p20 / total]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="raw/mock_campaign.csv")
    args = parser.parse_args()

    data = generate(args.n, args.seed)
    data.to_csv(args.out, index=False)
    print(f"Wrote {len(data)} rows to {args.out}")
