"""End-to-end workflow verification script.

Exercises the complete API workflow:
  Register -> Login -> Upload dataset -> Create run -> Poll -> Verify endpoints
  -> Scenario simulator -> Reports -> Assistant -> History -> Cross-user access denied
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def api(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = kwargs.pop("json", None)
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            if "application/pdf" in content_type or "text/csv" in content_type:
                return resp.status, raw
            body = raw.decode("utf-8")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def wait_for_run(token, run_id, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        status, data = api("GET", f"/runs/{run_id}", token=token)
        if status != 200:
            return None
        if data.get("status") in ("complete", "failed"):
            return data
        time.sleep(2)
    return None


def main():
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    print("=== EconoCausal End-to-End Workflow Verification ===\n")

    # 1. Register User 1
    print("[1] Registering User 1...")
    status, user1 = api("POST", "/auth/register", json={
        "email": f"e2e_user1_{ts}@test.com",
        "password": "pass12345",
        "full_name": "E2E User 1",
    })
    assert status == 201, f"Register failed: {user1}"
    token1 = user1["access_token"]
    user1_id = user1["user"]["user_id"]
    print(f"    User 1 ID: {user1_id}")

    # 2. Register User 2
    print("[2] Registering User 2...")
    status, user2 = api("POST", "/auth/register", json={
        "email": f"e2e_user2_{ts}@test.com",
        "password": "pass12345",
        "full_name": "E2E User 2",
    })
    assert status == 201, f"Register failed: {user2}"
    token2 = user2["access_token"]
    user2_id = user2["user"]["user_id"]
    print(f"    User 2 ID: {user2_id}")

    # 3. Create dataset with CUSTOM column names
    print("[3] Creating dataset with custom columns (discount_given, purchase_result)...")
    rows = []
    for i in range(40):
        loyalty = (i % 10) / 10.0
        discount_given = [0.0, 10.0, 20.0][i % 3]
        purchase_result = 1 if (loyalty + discount_given / 100.0) > 0.6 else 0
        rows.append({
            "features": {"customer_age": float(20 + i), "income": float(30000 + i * 1000)},
            "treatment": discount_given,
            "outcome": purchase_result,
        })
    status, dataset = api("POST", "/datasets", json={"name": "e2e_custom_cols", "rows": rows}, token=token1)
    assert status == 201, f"Dataset creation failed: {dataset}"
    dataset_id = dataset["dataset_id"]
    print(f"    Dataset ID: {dataset_id}")

    # 3a. Verify User 2 cannot create a run on User 1's dataset
    print("[3a] Verifying User 2 cannot use User 1's dataset...")
    status, data = api("POST", "/runs", token=token2, json={
        "dataset_id": dataset_id,
        "budget": 200,
        "base_estimator": "RandomForest",
        "campaign_name": "Cross-user dataset access",
    })
    assert status == 404, f"User 2 should get 404 using User 1's dataset, got {status}"
    print("    User 2 correctly blocked from User 1's dataset (404)")

    # 3b. Verify anonymous cannot create dataset
    print("[3b] Verifying anonymous cannot create dataset...")
    status, data = api("POST", "/datasets", json={"name": "anon_ds", "rows": [
        {"features": {"x": 1.0}, "treatment": 0.0, "outcome": 1}
    ]})
    assert status == 401, f"Anonymous should get 401 creating dataset, got {status}"
    print("    Anonymous correctly blocked from dataset creation (401)")

    # 4. Create run with custom treatment/outcome columns
    print("[4] Creating run with custom column mapping...")
    status, run = api("POST", "/runs", token=token1, json={
        "dataset_id": dataset_id,
        "budget": 200,
        "base_estimator": "RandomForest",
        "campaign_name": "E2E Custom Column Test",
        "treatment_column": "discount_given",
        "outcome_column": "purchase_result",
        "discount_levels": [0, 10, 20],
    })
    assert status == 202, f"Run creation failed: {run}"
    run_id = run["run_id"]
    print(f"    Run ID: {run_id}, initial status: {run['status']}")

    # 5. Wait for completion
    print("[5] Waiting for run to complete...")
    run = wait_for_run(token1, run_id)
    assert run is not None, "Run did not complete in time"
    assert run["status"] == "complete", f"Run failed: {run}"
    print(f"    Run completed successfully")

    # 6. Verify all endpoints
    endpoints = [
        ("GET", f"/runs/{run_id}"),
        ("GET", f"/runs/{run_id}/summary"),
        ("GET", f"/runs/{run_id}/analytics"),
        ("GET", f"/runs/{run_id}/explainability"),
        ("GET", f"/runs/{run_id}/recommendations"),
        ("GET", f"/runs/{run_id}/allocation"),
        ("GET", f"/runs/{run_id}/refutation"),
        ("GET", f"/runs/{run_id}/drift"),
        ("GET", f"/runs/{run_id}/ite"),
    ]
    print("[6] Verifying all run endpoints...")
    for method, path in endpoints:
        status, data = api(method, path, token=token1)
        assert status == 200, f"{method} {path} failed: {status} {data}"
    print("    All endpoints returned 200")

    # Get a valid customer ID for explanation test
    status, alloc_data = api("GET", f"/runs/{run_id}/allocation", token=token1)
    assert status == 200
    valid_customer_id = alloc_data["allocations"][0]["customer_id"]
    print(f"    Valid customer ID for explanation: {valid_customer_id}")

    # Verify customer explanation endpoint
    status, data = api("GET", f"/runs/{run_id}/customers/{valid_customer_id}/explanation", token=token1)
    assert status == 200, f"Customer explanation failed: {status} {data}"
    print("    Customer explanation returned 200")

    all_endpoints = endpoints + [("GET", f"/runs/{run_id}/customers/{valid_customer_id}/explanation")]

    # 7. Verify ownership enforcement
    print("[7] Verifying ownership enforcement (User 2)...")
    for method, path in all_endpoints:
        status, data = api(method, path, token=token2)
        assert status == 404, f"User 2 should get 404 on {method} {path}, got {status}"
    print("    User 2 correctly blocked (404)")

    # 8. Verify anonymous access denied
    print("[8] Verifying anonymous access denied...")
    for method, path in all_endpoints:
        status, data = api(method, path)
        assert status == 401, f"Anonymous should get 401 on {method} {path}, got {status}"
    print("    Anonymous correctly blocked (401)")

    # 9. Scenario simulator
    print("[9] Testing scenario simulator...")
    status, scenario = api("POST", f"/runs/{run_id}/simulate", token=token1, json={
        "budget": 100,
        "discount_levels": [0.0, 10.0],
    })
    assert status == 200, f"Scenario failed: {scenario}"
    assert scenario["total_budget_used"] <= 100
    print(f"    Scenario: budget_used={scenario['total_budget_used']:.2f}, targeted={scenario['customers_targeted']}")

    # 10. Scenario with invalid discount levels
    status, data = api("POST", f"/runs/{run_id}/simulate", token=token1, json={
        "budget": 100,
        "discount_levels": [999.0],
    })
    assert status == 422, f"Invalid scenario should fail: {status}"
    print("    Invalid discount levels correctly rejected (422)")

    # 11. Report download (via API, not browser)
    print("[10] Testing report generation...")
    status, csv_data = api("GET", f"/runs/{run_id}/report.csv", token=token1)
    assert status == 200, f"CSV report failed: {status}"
    assert isinstance(csv_data, bytes) and len(csv_data) > 0
    print(f"    CSV report generated ({len(csv_data)} bytes)")

    status, pdf_data = api("GET", f"/runs/{run_id}/report.pdf", token=token1)
    assert status == 200, f"PDF report failed: {status}"
    assert isinstance(pdf_data, bytes) and len(pdf_data) > 0
    print(f"    PDF report generated ({len(pdf_data)} bytes)")

    # 12. Assistant
    print("[11] Testing assistant...")
    status, answer_data = api("POST", f"/runs/{run_id}/assistant", token=token1, json={
        "question": "What is the budget utilization?",
    })
    assert status == 200, f"Assistant failed: {answer_data}"
    answer = answer_data["answer"]
    assert "budget" in answer.lower()
    print(f"    Assistant answered: {answer[:80]}...")

    # 13. History
    print("[12] Testing history...")
    status, history = api("GET", "/campaigns", token=token1)
    assert status == 200
    assert len(history["campaigns"]) >= 1
    assert any(c["run_id"] == run_id for c in history["campaigns"])
    print(f"    History contains {len(history['campaigns'])} campaigns")

    # 14. User 2 history should be empty
    status, history2 = api("GET", "/campaigns", token=token2)
    assert status == 200
    assert all(c["run_id"] != run_id for c in history2["campaigns"])
    print("    User 2 history does not contain User 1's run")

    # 15. Anonymous history denied
    status, _ = api("GET", "/campaigns")
    assert status == 401
    print("    Anonymous history correctly blocked (401)")

    print("\n=== END-TO-END VERIFICATION COMPLETE: ALL CHECKS PASSED ===")


if __name__ == "__main__":
    main()
