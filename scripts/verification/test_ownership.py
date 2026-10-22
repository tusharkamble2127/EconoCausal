import urllib.request
import urllib.error
import json

base = "http://127.0.0.1:8000"

def api(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

import time
ts = int(time.time())
email1 = f"u1_{ts}@test.com"
email2 = f"u2_{ts}@test.com"

s1, r1 = api("POST", "/auth/register", {"email": email1, "password": "pass123", "full_name": "U1"})
token1 = r1.get("access_token")

s2, r2 = api("POST", "/auth/register", {"email": email2, "password": "pass123", "full_name": "U2"})
token2 = r2.get("access_token")

rows = []
for i in range(30):
    treatment = [0.0, 10.0, 20.0][i % 3]
    outcome = 1 if i % 2 == 0 else 0
    rows.append({"features": {"loyalty_score": (i % 10) / 10.0, "tenure_months": float(i)}, "treatment": treatment, "outcome": outcome})
s, ds = api("POST", "/datasets", {"name": f"u1ds_{ts}", "rows": rows}, token1)

s, run = api("POST", "/runs", {"dataset_id": ds.get("dataset_id"), "budget": 100, "base_estimator": "RandomForest", "campaign_name": "U1 Run"}, token1)
run_id = run.get("run_id")
print(f"Run ID: {run_id}")

# Check history for user1
s, hist1 = api("GET", "/campaigns", token=token1)
print("User1 history:", [c["run_id"] for c in hist1.get("campaigns", [])])

# Check history for user2
s, hist2 = api("GET", "/campaigns", token=token2)
print("User2 history:", [c["run_id"] for c in hist2.get("campaigns", [])])

# User2 tries to access user1's run
s2acc, resp2 = api("GET", f"/runs/{run_id}/summary", token=token2)
print("User2 access status:", s2acc, resp2)

# User1 accesses their own run
s1acc, resp1 = api("GET", f"/runs/{run_id}/summary", token=token1)
print("User1 access status:", s1acc)
