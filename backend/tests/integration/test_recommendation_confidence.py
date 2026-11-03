"""
Regression tests for the recommendation panel's confidence_score
(Enhancement #6), added during the forensic debugging pass.

Two real bugs were found and fixed here, in sequence:
  1. The original "dose-spread consistency" formula was mathematically
     constant across every customer for a LinearDML model, because the
     model's effect is linear in the treatment dose -- the ratio between
     any two doses' ITE is identical for everyone by construction.
  2. The first CI-based fix normalized interval width by the point
     estimate's own (often small) magnitude, which clamped to zero
     confidence for nearly every customer whose CI happened to be wider
     than its own point estimate -- common for noisy probability-uplift
     estimates and not actually a sign of total uncertainty.

These tests assert the actual, user-visible symptom of each bug (every
customer receiving the identical confidence_score) does not recur,
using a dataset large and noisy enough to exercise the code path that
was previously constant.
"""
import random

import pandas as pd
import pytest


@pytest.fixture()
def noisy_dataset_payload():
    random.seed(7)
    rows = []
    for i in range(200):
        loyalty = random.random()
        tenure = random.randint(1, 60)
        aov = random.uniform(20, 100)
        treatment = random.choice([0.0, 10.0, 20.0])
        p = 0.15 + 0.3 * loyalty + treatment * 0.004
        outcome = 1 if random.random() < p else 0
        rows.append(
            {
                "features": {"loyalty_score": loyalty, "tenure_months": tenure, "avg_order_value": aov},
                "treatment": treatment,
                "outcome": outcome,
            }
        )
    return {"name": "confidence_regression_dataset", "rows": rows}


def test_confidence_score_varies_across_customers(client, noisy_dataset_payload, owner_headers):
    """The core regression check: confidence_score must not collapse to a
    single constant value across the whole customer base. Both historical
    bugs produced exactly this symptom (all 0.5, then all 0.5/1.0)."""
    dataset_id = client.post("/datasets", json=noisy_dataset_payload, headers=owner_headers).json()["dataset_id"]
    run = client.post(
        "/runs",
        json={"dataset_id": dataset_id, "budget": 500, "campaign_name": "Confidence Regression"},
        headers=owner_headers,
    ).json()

    resp = client.get(f"/runs/{run['run_id']}/recommendations", headers=owner_headers)
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) == len(noisy_dataset_payload["rows"])

    scores = [r["confidence_score"] for r in recs]
    unique_scores = set(scores)

    # A real per-customer signal should produce meaningfully more than a
    # handful of distinct values across 200 different customers.
    assert len(unique_scores) > 10, f"confidence_score looks collapsed to a small constant set: {unique_scores}"
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_confidence_score_for_targeted_customers_is_not_a_single_constant(client, noisy_dataset_payload, owner_headers):
    """Specifically targets the group that both historical bugs collapsed:
    customers who actually received a non-zero discount."""
    dataset_id = client.post("/datasets", json=noisy_dataset_payload, headers=owner_headers).json()["dataset_id"]
    run = client.post(
        "/runs",
        json={"dataset_id": dataset_id, "budget": 500, "campaign_name": "Confidence Regression 2"},
        headers=owner_headers,
    ).json()

    recs = client.get(f"/runs/{run['run_id']}/recommendations", headers=owner_headers).json()["recommendations"]
    targeted_scores = [r["confidence_score"] for r in recs if r["recommended_discount"] > 0]

    assert len(targeted_scores) > 0, "test setup problem: no customer was targeted with a discount"
    assert len(set(targeted_scores)) > 1, (
        "confidence_score is a single constant across every targeted customer -- "
        "this is the exact symptom of the two historical bugs (see module docstring)"
    )


def test_confidence_is_consistent_across_endpoints(client, noisy_dataset_payload, owner_headers):
    """The same customer must receive the same confidence_score from the
    recommendation panel and the per-customer explanation endpoint."""
    dataset_id = client.post("/datasets", json=noisy_dataset_payload, headers=owner_headers).json()["dataset_id"]
    run = client.post(
        "/runs",
        json={"dataset_id": dataset_id, "budget": 500, "campaign_name": "Confidence Consistency"},
        headers=owner_headers,
    ).json()
    run_id = run["run_id"]

    recs = client.get(f"/runs/{run_id}/recommendations", headers=owner_headers).json()["recommendations"]
    rec_lookup = {r["customer_id"]: r["confidence_score"] for r in recs}

    for customer_id, rec_score in rec_lookup.items():
        resp = client.get(f"/runs/{run_id}/customers/{customer_id}/explanation", headers=owner_headers)
        assert resp.status_code == 200
        expl_score = resp.json()["confidence_score"]
        assert expl_score == rec_score, (
            f"Confidence mismatch for customer {customer_id}: recommendations={rec_score}, explanation={expl_score}"
        )
