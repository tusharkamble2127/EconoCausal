"""
Permanent regression tests for run-level authorization (Step 10).

Covers:
  - owner can access own run
  - different authenticated user cannot access run (404, no data leak)
  - anonymous user cannot access protected run (401)
  - invalid run ID returns 404
  - campaign list is owner-scoped
  - report download is owner-scoped
  - customer explanation is owner-scoped
  - ITE / prediction results are owner-scoped
  - scenario simulator is owner-scoped
  - assistant endpoint is owner-scoped
"""
from __future__ import annotations

import pytest


OWNERSHIP_TEST_PATHS = [
    ("GET", "/runs/{run_id}"),
    ("GET", "/runs/{run_id}/summary"),
    ("GET", "/runs/{run_id}/analytics"),
    ("GET", "/runs/{run_id}/explainability"),
    ("GET", "/runs/{run_id}/recommendations"),
    ("GET", "/runs/{run_id}/allocation"),
    ("GET", "/runs/{run_id}/refutation"),
    ("GET", "/runs/{run_id}/drift"),
    ("GET", "/runs/{run_id}/report.csv"),
    ("GET", "/runs/{run_id}/report.pdf"),
    ("GET", "/runs/{run_id}/ite"),
    ("GET", "/runs/{run_id}/propensity"),
    ("GET", "/runs/{run_id}/customers/1/explanation"),
]


@pytest.fixture()
def owner_run(client, sample_dataset_payload, owner_headers):
    """Create a dataset and a completed run owned by ``owner_user``.

    Returns the run_id.
    """
    ds_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={"dataset_id": dataset_id, "budget": 200, "base_estimator": "RandomForest", "campaign_name": "Audit Run"},
        headers=owner_headers,
    )
    assert run_resp.status_code == 202
    assert run_resp.json()["status"] == "complete"
    return run_resp.json()["run_id"]


class TestOwnerAccess:
    """Owner of the run can access every protected endpoint."""

    @pytest.mark.parametrize("method,path", OWNERSHIP_TEST_PATHS)
    def test_owner_can_access_own_run(self, client, owner_run, owner_headers, method, path):
        resolved = path.replace("{run_id}", str(owner_run))
        resp = client.request(method, resolved, headers=owner_headers)
        assert resp.status_code == 200, (
            f"Owner should get 200 for {resolved}, got {resp.status_code}: {resp.text[:200]}"
        )


class TestNonOwnerAccess:
    """A different authenticated user must not see the owner's run data."""

    @pytest.mark.parametrize("method,path", OWNERSHIP_TEST_PATHS)
    def test_different_user_cannot_access_run(self, client, owner_run, other_headers, method, path):
        resolved = path.replace("{run_id}", str(owner_run))
        resp = client.request(method, resolved, headers=other_headers)
        assert resp.status_code == 404, (
            f"Non-owner should get 404 for {resolved}, got {resp.status_code}"
        )
        # Verify the response body does NOT contain run data
        body = resp.text
        assert "Audit Run" not in body, f"Response leaks campaign name: {body[:200]}"


class TestAnonymousAccess:
    """Anonymous (no token) users must be rejected with 401."""

    @pytest.mark.parametrize("method,path", OWNERSHIP_TEST_PATHS)
    def test_anonymous_cannot_access_protected_run(self, client, owner_run, method, path):
        resolved = path.replace("{run_id}", str(owner_run))
        resp = client.request(method, resolved)
        assert resp.status_code == 401, (
            f"Anonymous should get 401 for {resolved}, got {resp.status_code}"
        )


def test_invalid_run_id_returns_404(client, owner_headers):
    """A non-existent run ID returns 404, not 500 or data."""
    resp = client.get("/runs/99999/summary", headers=owner_headers)
    assert resp.status_code == 404
    assert resp.json()["error"] == "RunNotFoundError"


def test_campaign_list_is_owner_scoped(client, owner_run, owner_headers, other_headers):
    """User 1 sees their own campaigns; User 2 sees only theirs (none)."""
    # Owner sees their run
    resp = client.get("/campaigns", headers=owner_headers)
    assert resp.status_code == 200
    campaigns = resp.json()["campaigns"]
    run_ids = [c["run_id"] for c in campaigns]
    assert any(rid == owner_run for rid in run_ids), f"Owner should see run {owner_run}: {run_ids}"

    # Non-owner does NOT see the owner's run
    resp = client.get("/campaigns", headers=other_headers)
    assert resp.status_code == 200
    campaigns = resp.json()["campaigns"]
    run_ids = [c["run_id"] for c in campaigns]
    assert owner_run not in run_ids, f"Non-owner should NOT see run {owner_run}: {run_ids}"

    # Anonymous cannot list campaigns at all
    resp = client.get("/campaigns")
    assert resp.status_code == 401


def test_report_download_is_owner_scoped(client, owner_run, owner_headers, other_headers):
    """CSV and PDF reports are blocked for non-owners and anonymous."""
    for ext in ["csv", "pdf"]:
        # Owner can download
        resp = client.get(f"/runs/{owner_run}/report.{ext}", headers=owner_headers)
        assert resp.status_code == 200, f"Owner should download report.{ext}"

        # Non-owner is blocked
        resp = client.get(f"/runs/{owner_run}/report.{ext}", headers=other_headers)
        assert resp.status_code == 404, f"Non-owner should get 404 for report.{ext}"

        # Anonymous is blocked
        resp = client.get(f"/runs/{owner_run}/report.{ext}")
        assert resp.status_code == 401, f"Anonymous should get 401 for report.{ext}"


def test_customer_explanation_is_owner_scoped(client, owner_run, owner_headers, other_headers):
    """Per-customer explanation is blocked for non-owners and anonymous."""
    path = f"/runs/{owner_run}/customers/1/explanation"

    # Owner can access
    resp = client.get(path, headers=owner_headers)
    assert resp.status_code == 200, f"Owner should get 200: {resp.text[:200]}"

    # Non-owner is blocked
    resp = client.get(path, headers=other_headers)
    assert resp.status_code == 404, f"Non-owner should get 404"

    # Anonymous is blocked
    resp = client.get(path)
    assert resp.status_code == 401, f"Anonymous should get 401"


def test_scenario_simulator_is_owner_scoped(client, owner_run, owner_headers, other_headers):
    """POST /runs/{run_id}/simulate is blocked for non-owners and anonymous."""
    path = f"/runs/{owner_run}/simulate"
    payload = {"budget": 100, "discount_levels": [0.0, 10.0, 20.0]}

    # Owner can simulate
    resp = client.post(path, json=payload, headers=owner_headers)
    assert resp.status_code == 200, f"Owner should simulate: {resp.text[:200]}"

    # Non-owner is blocked
    resp = client.post(path, json=payload, headers=other_headers)
    assert resp.status_code == 404, f"Non-owner should get 404 for simulate"

    # Anonymous is blocked
    resp = client.post(path, json=payload)
    assert resp.status_code == 401, f"Anonymous should get 401 for simulate"


def test_assistant_is_owner_scoped(client, owner_run, owner_headers, other_headers):
    """POST /runs/{run_id}/assistant is blocked for non-owners and anonymous."""
    path = f"/runs/{owner_run}/assistant"
    payload = {"query": "What are the key findings?"}

    # Owner can ask
    resp = client.post(path, json=payload, headers=owner_headers)
    assert resp.status_code == 200, f"Owner should get 200: {resp.text[:200]}"

    # Non-owner is blocked
    resp = client.post(path, json=payload, headers=other_headers)
    assert resp.status_code == 404, f"Non-owner should get 404 for assistant"

    # Anonymous is blocked
    resp = client.post(path, json=payload)
    assert resp.status_code == 401, f"Anonymous should get 401 for assistant"


def test_post_run_requires_auth(client, sample_dataset_payload, owner_headers):
    """POST /runs requires authentication -- anonymous users get 401."""
    ds_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
    dataset_id = ds_resp.json()["dataset_id"]

    resp = client.post("/runs", json={"dataset_id": dataset_id, "budget": 100, "base_estimator": "RandomForest"})
    assert resp.status_code == 401


class TestDatasetOwnership:
    """Datasets are scoped to the authenticated user who created them."""

    def test_owner_can_create_dataset(self, client, owner_headers):
        resp = client.post("/datasets", json={"name": "owner_ds", "rows": [
            {"features": {"x": 1.0}, "treatment": 0.0, "outcome": 1}
        ]}, headers=owner_headers)
        assert resp.status_code == 201
        assert resp.json()["dataset_id"] == 1

    def test_anonymous_cannot_create_dataset(self, client, sample_dataset_payload):
        resp = client.post("/datasets", json=sample_dataset_payload)
        assert resp.status_code == 401

    def test_user2_cannot_create_run_on_user1_dataset(self, client, owner_headers, other_headers, sample_dataset_payload):
        ds_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = ds_resp.json()["dataset_id"]

        resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 100, "base_estimator": "RandomForest"},
            headers=other_headers,
        )
        assert resp.status_code == 404

    def test_user2_cannot_access_user1_dataset_indirectly_via_run(self, client, owner_headers, other_headers, sample_dataset_payload):
        ds_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = ds_resp.json()["dataset_id"]

        run_resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 100, "base_estimator": "RandomForest", "campaign_name": "Owner Run"},
            headers=owner_headers,
        )
        assert run_resp.status_code == 202
        run_id = run_resp.json()["run_id"]

        resp = client.get(f"/runs/{run_id}/summary", headers=other_headers)
        assert resp.status_code == 404
        assert "Owner Run" not in resp.text
