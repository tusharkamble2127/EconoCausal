"""Integration tests for application-wide issues found during the full audit."""
from __future__ import annotations


class TestColumnMappingIntegration:
    """The backend pipeline must work end-to-end when the user selects
    custom treatment/outcome column names in the UI."""

    def test_full_run_with_custom_columns(self, client, owner_headers):
        rows = []
        for i in range(30):
            loyalty = (i % 10) / 10.0
            discount_given = [0.0, 10.0, 20.0][i % 3]
            purchase_result = 1 if (loyalty + discount_given / 100.0) > 0.5 else 0
            rows.append(
                {
                    "features": {"customer_age": float(20 + i), "income": float(30000 + i * 1000)},
                    "treatment": discount_given,
                    "outcome": purchase_result,
                }
            )
        dataset_resp = client.post("/datasets", json={"name": "custom_cols", "rows": rows}, headers=owner_headers)
        assert dataset_resp.status_code == 201
        dataset_id = dataset_resp.json()["dataset_id"]

        run_resp = client.post(
            "/runs",
            json={
                "dataset_id": dataset_id,
                "budget": 150,
                "base_estimator": "RandomForest",
                "treatment_column": "discount_given",
                "outcome_column": "purchase_result",
            },
            headers=owner_headers,
        )
        assert run_resp.status_code == 202
        run_body = run_resp.json()
        assert run_body["status"] == "complete"

        alloc_resp = client.get(f"/runs/{run_body['run_id']}/allocation", headers=owner_headers)
        assert alloc_resp.status_code == 200
        assert alloc_resp.json()["total_budget_used"] <= 150

    def test_recommendations_with_custom_columns(self, client, owner_headers):
        rows = []
        for i in range(20):
            loyalty = (i % 5) / 5.0
            discount_given = [0.0, 10.0][i % 2]
            purchase_result = 1 if loyalty > 0.5 else 0
            rows.append(
                {
                    "features": {"loyalty_score": loyalty},
                    "treatment": discount_given,
                    "outcome": purchase_result,
                }
            )
        dataset_resp = client.post("/datasets", json={"name": "custom_cols_rec", "rows": rows}, headers=owner_headers)
        assert dataset_resp.status_code == 201
        dataset_id = dataset_resp.json()["dataset_id"]

        run_resp = client.post(
            "/runs",
            json={
                "dataset_id": dataset_id,
                "budget": 50,
                "base_estimator": "RandomForest",
                "treatment_column": "discount_given",
                "outcome_column": "purchase_result",
            },
            headers=owner_headers,
        )
        assert run_resp.status_code == 202
        run_id = run_resp.json()["run_id"]

        rec_resp = client.get(f"/runs/{run_id}/recommendations", headers=owner_headers)
        assert rec_resp.status_code == 200
        assert len(rec_resp.json()["recommendations"]) == 20


class TestScenarioValidationIntegration:
    def test_scenario_rejects_invalid_discount_levels(self, client, owner_headers):
        rows = [
            {"features": {"loyalty": 0.5}, "treatment": 0.0, "outcome": 1},
            {"features": {"loyalty": 0.8}, "treatment": 10.0, "outcome": 0},
        ]
        dataset_resp = client.post("/datasets", json={"name": "scenario_test", "rows": rows}, headers=owner_headers)
        assert dataset_resp.status_code == 201
        dataset_id = dataset_resp.json()["dataset_id"]

        run_resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 50, "base_estimator": "RandomForest"},
            headers=owner_headers,
        )
        assert run_resp.status_code == 202
        run_id = run_resp.json()["run_id"]

        sim_resp = client.post(
            f"/runs/{run_id}/simulate",
            json={"budget": 50, "discount_levels": [999.0]},
            headers=owner_headers,
        )
        assert sim_resp.status_code == 422

    def test_scenario_accepts_subset_of_levels(self, client, owner_headers):
        rows = [
            {"features": {"loyalty": 0.5}, "treatment": 0.0, "outcome": 1},
            {"features": {"loyalty": 0.8}, "treatment": 10.0, "outcome": 0},
        ]
        dataset_resp = client.post("/datasets", json={"name": "scenario_subset", "rows": rows}, headers=owner_headers)
        assert dataset_resp.status_code == 201
        dataset_id = dataset_resp.json()["dataset_id"]

        run_resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 50, "base_estimator": "RandomForest"},
            headers=owner_headers,
        )
        assert run_resp.status_code == 202
        run_id = run_resp.json()["run_id"]

        sim_resp = client.post(
            f"/runs/{run_id}/simulate",
            json={"budget": 50, "discount_levels": [0.0, 10.0]},
            headers=owner_headers,
        )
        assert sim_resp.status_code == 200


class TestDatasetValidationIntegration:
    def test_dataset_rejects_empty_rows(self, client, owner_headers):
        resp = client.post("/datasets", json={"name": "empty_rows", "rows": []}, headers=owner_headers)
        assert resp.status_code == 422

    def test_run_rejects_negative_budget(self, client, owner_headers, sample_dataset_payload):
        dataset_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = dataset_resp.json()["dataset_id"]
        resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": -1, "base_estimator": "RandomForest"},
            headers=owner_headers,
        )
        assert resp.status_code == 422

    def test_run_rejects_unsupported_estimator(self, client, owner_headers, sample_dataset_payload):
        dataset_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = dataset_resp.json()["dataset_id"]
        resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 100, "base_estimator": "GradientBoosting"},
            headers=owner_headers,
        )
        assert resp.status_code == 422

    def test_run_rejects_empty_discount_levels(self, client, owner_headers, sample_dataset_payload):
        dataset_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = dataset_resp.json()["dataset_id"]
        resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 100, "discount_levels": []},
            headers=owner_headers,
        )
        assert resp.status_code == 422

    def test_run_rejects_duplicate_discount_levels(self, client, owner_headers, sample_dataset_payload):
        dataset_resp = client.post("/datasets", json=sample_dataset_payload, headers=owner_headers)
        dataset_id = dataset_resp.json()["dataset_id"]
        resp = client.post(
            "/runs",
            json={"dataset_id": dataset_id, "budget": 100, "discount_levels": [10.0, 10.0]},
            headers=owner_headers,
        )
        assert resp.status_code == 422
