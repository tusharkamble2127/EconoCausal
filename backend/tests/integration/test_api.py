"""
Integration tests for the API (Volume II Chapter 12, Day 23; Chapter 13.2).

Exercises the real routers, services, repositories, and pipeline together
against an in-memory SQLite database (see conftest.py), matching Volume I
Chapter 13.6's end-to-end integration testing requirement.
"""
from __future__ import annotations


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_dataset(client, sample_dataset_payload, owner_headers):
    resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["row_count"] == len(sample_dataset_payload["rows"])
    assert body["dataset_id"] == 1


def test_full_run_lifecycle(client, sample_dataset_payload, owner_headers):
    dataset_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
    dataset_id = dataset_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs", json={"dataset_id": dataset_id, "budget": 200, "base_estimator": "RandomForest"},
        headers=owner_headers,
    )
    assert run_resp.status_code == 202
    run_body = run_resp.json()
    assert run_body["status"] == "complete"
    run_id = run_body["run_id"]

    # GET /runs/{run_id}
    status_resp = client.get(f"/runs/{run_id}", headers=owner_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "complete"

    # GET /runs/{run_id}/ite
    ite_resp = client.get(f"/runs/{run_id}/ite", headers=owner_headers)
    assert ite_resp.status_code == 200
    scores = ite_resp.json()["scores"]
    assert len(scores) == len(sample_dataset_payload["rows"]) * 7  # 7 candidate discount levels

    # GET /runs/{run_id}/allocation
    alloc_resp = client.get(f"/runs/{run_id}/allocation", headers=owner_headers)
    assert alloc_resp.status_code == 200
    alloc_body = alloc_resp.json()
    assert alloc_body["total_budget_used"] <= 200
    assert len(alloc_body["allocations"]) == len(sample_dataset_payload["rows"])

    # GET /runs/{run_id}/refutation
    refutation_resp = client.get(f"/runs/{run_id}/refutation", headers=owner_headers)
    assert refutation_resp.status_code == 200
    tests = refutation_resp.json()["tests"]
    assert {t["test_name"] for t in tests} == {"placebo_treatment", "random_common_cause", "data_subset"}

    # GET /runs/{run_id}/propensity
    propensity_resp = client.get(f"/runs/{run_id}/propensity", headers=owner_headers)
    assert propensity_resp.status_code == 200
    propensity_body = propensity_resp.json()
    assert propensity_body["run_id"] == run_id
    assert "binary" in propensity_body or "continuous" in propensity_body


def test_propensity_for_unknown_run_returns_404(client, owner_headers):
    resp = client.get("/runs/9999/propensity", headers=owner_headers)
    assert resp.status_code == 404
    assert resp.json()["error"] == "RunNotFoundError"


def test_run_with_unknown_dataset_returns_404(client, owner_headers):
    resp = client.post(
        "/runs", json={"dataset_id": 9999, "budget": 100, "base_estimator": "RandomForest"},
        headers=owner_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "DatasetNotFoundError"


def test_ite_for_unknown_run_returns_404(client, owner_headers):
    resp = client.get("/runs/9999/ite", headers=owner_headers)
    assert resp.status_code == 404
    assert resp.json()["error"] == "RunNotFoundError"


def test_dataset_with_missing_fields_returns_422(client, owner_headers):
    resp = client.post("/datasets", json={"name": "bad"}, headers=owner_headers)
    assert resp.status_code == 422


def test_anonymous_cannot_create_dataset(client, sample_dataset_payload):
    resp = client.post("/datasets", json=sample_dataset_payload)
    assert resp.status_code == 401
