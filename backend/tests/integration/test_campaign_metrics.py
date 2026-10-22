"""
Regression test for app/services/campaign_metrics.py's blanket-targeting
baseline comparison, added during the forensic debugging pass.

BUG: the blanket baseline summed the blanket-discount-level ITE across
ALL customers in the dataset, not just the number actually targeted by
the real (budget-constrained) campaign. That silently compared a small,
budget-constrained real spend (e.g. $5,000 targeting 250 of 1,500
customers) against an unconstrained hypothetical of giving *everyone*
the discount (e.g. $30,000 across all 1,500) -- a ~6x larger implied
budget -- which always made the blanket baseline look artificially more
profitable in absolute terms. The visible symptom was a negative
"savings_vs_blanket" even for a campaign that was, per dollar spent,
strictly better than random targeting (confirmed live: -$10,122.45
"savings" on a real run, which is nonsensical for an optimizer that
always selects the highest-ITE customers first).

This test doesn't assert an exact number (that would be brittle against
model non-determinism), but it does assert the qualitative property the
bug violated: a causally-optimized allocation must never look worse
than a same-budget random/blanket allocation, since the optimizer is
mathematically guaranteed to select the best customers for the budget
it's given.
"""


def test_savings_vs_blanket_is_never_negative_for_an_optimal_allocation(client, owner_headers):
    """The optimizer always selects the highest-ITE customers for the
    budget it's given, so a fair (budget-normalized) comparison against
    a same-budget blanket/random baseline should never show the causal
    strategy losing to blanket targeting."""
    import random

    random.seed(3)
    rows = []
    for i in range(400):
        loyalty = random.random()
        treatment = random.choice([0.0, 10.0, 20.0])
        p = 0.15 + 0.3 * loyalty + treatment * 0.004
        outcome = 1 if random.random() < p else 0
        rows.append(
            {
                "features": {"loyalty_score": loyalty, "tenure_months": float(random.randint(1, 60))},
                "treatment": treatment,
                "outcome": outcome,
            }
        )

    dataset_id = client.post("/datasets", json={"name": "savings_regression", "rows": rows}, headers=owner_headers).json()["dataset_id"]
    run = client.post(
        "/runs",
        json={"dataset_id": dataset_id, "budget": 500, "campaign_name": "Savings Regression"},
        headers=owner_headers,
    ).json()

    summary = client.get(f"/runs/{run['run_id']}/summary", headers=owner_headers).json()

    assert summary["savings_vs_blanket"] >= -0.01, (
        f"savings_vs_blanket is negative ({summary['savings_vs_blanket']}), which means the "
        "budget-optimal allocation looks worse than a same-budget blanket baseline -- "
        "this is the exact symptom of the historical blanket-baseline normalization bug"
    )

    # Sanity check the KPI fields this same bug also touched are self-consistent.
    assert summary["budget_used"] <= summary["budget"] + 0.01
    assert summary["customers_targeted"] <= summary["customers_total"]
