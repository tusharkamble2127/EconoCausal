# EconoCausal Security Audit Report

> **HISTORICAL SNAPSHOT — DO NOT TREAT AS CURRENT**
>
> **Date:** 2027-11-01
>
> This report is a time-bound snapshot from an earlier point in the project.
> It is preserved for historical reference only. Since this audit date, the
> test suite has grown and additional fixes were applied (see the root
> `README.md` for the current authoritative status):
>
> - **Test count:** This report references 181 passing tests. The current
>   suite has **190 tests** (9 password-reset integration tests were added
>   after this audit). See `docs/testing/testing_summary.md` for current
>   results.
> - **White-screen bugs:** Two critical runtime bugs were found and fixed
>   in `DashboardPage.jsx` (React hook ordering violation and missing
>   `InfoTooltip` import) — see `docs/testing/testing_summary.md` and
>   `QA_REPORT.md` for details.
> - **Axios timeout:** The frontend client timeout was updated to
>   **600 seconds** (600000 ms) — see `frontend/src/api/client.js`.
> - **Playwright timeout:** The full-verification campaign test timeout was
>   updated to **900 seconds** — see `frontend/tests/full-verification.spec.js`.
> - **Brevo verification:** Brevo API submission was tested; the request format
>   is correct and API credentials are loaded, but Brevo returns HTTP 401 due
>   to IP authorization restrictions in the current environment. The
>   application handles this gracefully (catches `EmailError`, returns generic
>   response). See `README.md` for current authoritative status.
>
> **Current status:** READY — ALL E2E TESTS PASS (190 backend, 25 Playwright).
> The root `README.md` is the authoritative entry point.

---

## 1. Executive Summary

The audit identified and fixed four remaining findings from the previous audit pass:

1. **JWT Secret Security** — The fallback secret `dev-only-insecure-secret-change-me` was silently accepted in all environments. A startup validation now rejects it in production.
2. **Dataset Ownership** — `POST /datasets` had no authentication, allowing anonymous users to create datasets. Datasets now require authentication and are scoped to the creating user. Runs verify dataset ownership.
3. **Confidence Score Consistency** — Two services used different formulas (`consistency` vs `precision`). A canonical `confidence_service.py` now computes the same score for recommendations and customer explanations.
4. **Unused Optional Auth Dependency** — `get_current_user_optional` was retained but unused after the auth bypass fix. It has been removed.

### Fixes Applied
- `app/core/config.py` — Added `app_env` and `__post_init__` validation that fails startup in production if `ECONOCAUSAL_JWT_SECRET` is missing or equals the insecure default.
- `app/models/dataset.py` — Added `owner_id` column.
- `app/repositories/dataset_repository.py` — `create` now requires `owner_id`; added `get_owned` and `list_by_owner`.
- `app/services/dataset_service.py` — `create_dataset` now accepts `owner_id`.
- `app/api/routes_dataset.py` — `POST /datasets` now requires `get_current_user`.
- `app/services/training_service.py` — Verifies dataset ownership before creating a run.
- `app/services/confidence_service.py` — **NEW** canonical confidence calculation.
- `app/services/explainability_service.py` — Uses canonical confidence service.
- `app/services/recommendation_service.py` — Uses canonical confidence service.
- `app/api/deps.py` — Removed unused `get_current_user_optional`.
- `.env.example` — **NEW** documentation for environment variables.

### Test Results
- **End-to-end live server test:** All workflow steps passed.
- **Pytest regression suite (re-verified on Python 3.12):** 181 tests collected, 181 passed, 0 failed.
- **Note:** As of the current state, the suite has grown to **190 tests** (9
  password-reset integration tests were added after this audit snapshot).
  See `docs/testing/testing_summary.md` for the current test inventory.

---

## 2. JWT Secret Security

### Finding
`app/core/config.py` used a hardcoded fallback:
```python
jwt_secret_key: str = os.environ.get("ECONOCAUSAL_JWT_SECRET", "dev-only-insecure-secret-change-me")
```
This allowed the insecure default to be silently used in production-like execution.

### Fix
Added `app_env` and `__post_init__` validation:
- **Development:** Insecure default allowed only when `ECONOCAUSAL_ENV=development`.
- **Production:** If `ECONOCAUSAL_JWT_SECRET` is missing or equals the insecure default, the application raises `ValueError` at import time and fails startup.

### Tests Added
- `tests/unit/test_config.py` — 5 tests covering valid secret, missing secret in production, insecure default in production, development mode behavior.

---

## 3. Dataset Ownership

### Finding
`POST /datasets` did not require authentication. Datasets were anonymous containers, but the application's security model associates all data with authenticated users.

### Fix
- **Model:** Added `owner_id` column to `Dataset`.
- **Repository:** `dataset_repository.create` now requires `owner_id`. Added `get_owned(db, dataset_id, owner_id)` and `list_by_owner(db, owner_id)`.
- **Service:** `dataset_service.create_dataset` accepts `owner_id`.
- **Route:** `POST /datasets` now uses `Depends(get_current_user)`.
- **Run creation:** `training_service.create_run` verifies that `dataset.owner_id == owner_id` before proceeding, returning 404 if mismatched.

### Verified
- User 1 → User 1 dataset = allowed
- User 2 → User 1 dataset = blocked (404)
- Anonymous → dataset creation = blocked (401)

---

## 4. Confidence Score Standardization

### Finding
Two services computed confidence differently:
- `explainability_service.py`: `0.5 * consistency + 0.5 * pass_rate` where `consistency` was based on ITE spread across discount levels (mathematically constant for LinearDML).
- `recommendation_service.py`: `0.5 * precision + 0.5 * pass_rate` where `precision` was based on CI width at the chosen discount level.

### Fix
Created `app/services/confidence_service.py` with a single canonical formula:
```python
precision = math.exp(-5.0 * width)  # width = ci_upper - ci_lower
confidence_score = 0.5 * precision + 0.5 * pass_rate
```
Both `explainability_service.py` and `recommendation_service.py` now use this shared function.

### Regression Test
`test_confidence_is_consistent_across_endpoints` verifies that the same customer receives the identical confidence score from both `/recommendations` and `/customers/{id}/explanation`.

---

## 5. Unused Optional Auth Dependency

### Finding
`get_current_user_optional` was retained in `app/api/deps.py` after the authentication bypass fix, but no route referenced it.

### Fix
Removed `get_current_user_optional` from `app/api/deps.py`. Updated `README.md` and `AUDIT_REPORT.md` to remove references.

---

## 6. End-to-End Authenticated Test Results

**Database state:** Fresh SQLite database
**User 1:** `user_id=1`
**User 2:** `user_id=2`

### 6.1 Live Server Tests

| Endpoint | User 1 (owner) | User 2 (non-owner) | Anonymous |
|----------|----------------|--------------------|-----------|
| POST /datasets | 201 | — | 401 |
| POST /runs | 202 | — | 401 |
| GET /runs/{run_id} | 200 | 404 | 401 |
| GET /runs/{run_id}/summary | 200 | 404 | 401 |
| GET /runs/{run_id}/analytics | 200 | 404 | 401 |
| GET /runs/{run_id}/explainability | 200 | 404 | 401 |
| GET /runs/{run_id}/recommendations | 200 | 404 | 401 |
| GET /runs/{run_id}/allocation | 200 | 404 | 401 |
| GET /runs/{run_id}/refutation | 200 | 404 | 401 |
| GET /runs/{run_id}/drift | 200 | 404 | 401 |
| GET /runs/{run_id}/report.csv | 200 | 404 | 401 |
| GET /runs/{run_id}/report.pdf | 200 | 404 | 401 |
| GET /runs/{run_id}/ite | 200 | 404 | 401 |
| GET /runs/{run_id}/customers/{cid}/explanation | 200 | 404 | 401 |
| POST /runs/{run_id}/simulate | 200 | 404 | 401 |
| POST /runs/{run_id}/assistant | 200 | 404 | 401 |
| GET /campaigns | 200 (own only) | 200 (empty) | 401 |
| GET /health | 200 | 200 | 200 |

### 6.2 Response Body Leak Check
For User 2 (non-owner) on all endpoints, the response body contains no run data.

### 6.3 Cross-User Dataset Isolation
- User 2 attempting to create a run on User 1's dataset receives 404.
- Anonymous users cannot create datasets (401).

---

## 7. Permanent Regression Tests

### 7.1 Unit Tests (110 tests)
| File | Tests |
|------|-------|
| `tests/unit/test_application_audit.py` | included in total |
| `tests/unit/test_cleaning.py` | 6 |
| `tests/unit/test_config.py` | 5 |
| `tests/unit/test_confidence_service.py` | 22 |
| `tests/unit/test_drift_detector.py` | 2 |
| `tests/unit/test_features.py` | 3 |
| `tests/unit/test_optimizer.py` | 4 |
| `tests/unit/test_propensity_score.py` | 18 |
| `tests/unit/test_report_service.py` | 2 |
| `tests/unit/test_validation.py` | 15 |
| Additional unit tests | remaining to reach 110 |

### 7.2 Integration Tests (71 tests)
| File | Tests |
|------|-------|
| `tests/integration/test_api.py` | 8 |
| `tests/integration/test_application_audit.py` | 9 |
| `tests/integration/test_campaign_metrics.py` | 1 |
| `tests/integration/test_ownership.py` | 47 |
| `tests/integration/test_recommendation_confidence.py` | 3 |
| Additional integration tests | remaining to reach 71 |

**Full test suite results:**
```
181 passed, 0 failed
```

### 7.3 Test Infrastructure Changes
- `tests/unit/test_config.py` — **NEW**: 5 JWT configuration validation tests
- `tests/integration/test_ownership.py` — Added 4 dataset ownership tests + updated fixtures to use auth
- `tests/integration/test_recommendation_confidence.py` — Added 1 confidence consistency regression test
- `tests/integration/test_api.py` — Updated dataset creation tests to use auth
- `tests/integration/test_application_audit.py` — Updated dataset creation tests to use auth
- `tests/integration/test_campaign_metrics.py` — Updated dataset creation to use auth
- `scripts/e2e/e2e_verify.py` — Updated to use authenticated dataset creation and added dataset ownership checks

---

## 8. Broader Project Audit

| Area | Status | Notes |
|------|--------|-------|
| Treatment/outcome mapping | OK | `CampaignConfigPage.jsx` maps CSV columns; backend pipeline uses fixed `"treatment"`/`"outcome"` keys |
| Discount $ vs % | OK | All discount levels are dollar amounts (e.g., 0, 10, 20); no $/% ambiguity |
| Estimator selection | OK | Only `RandomForest` is supported and validated in `RunCreateSchema` |
| CSV parsing | OK | Frontend handles quoted commas and escaped quotes; backend validates rows |
| Input validation | OK | Pydantic schemas validate all inputs; NaN/Infinity rejected |
| Database | OK | SQLite via SQLAlchemy; `owner_id` on datasets; ownership enforced at API layer |
| Authentication | FIXED | JWT required on all protected endpoints; production startup validates secret |
| Dataset ownership | FIXED | Datasets require auth and are scoped to owner; runs verify dataset ownership |
| Causal/ML pipeline | OK | `dml_model.py` (EconML LinearDML), `cleaning.py`, `features.py`, `causal_graph.py` (DoWhy) |
| Optimizer | OK | `optimizer.py` uses `scipy.optimize.milp` with dollar budget constraint |
| Dashboard | OK | All KPIs computed from actual backend data |
| Recommendations | OK | Confidence score now canonical and consistent across endpoints |
| Explainability | OK | Global and per-customer; uses canonical confidence service |
| Scenario simulator | OK | Validates discount levels; re-optimizes without retraining |
| Drift | OK | KS test per feature against previous run |
| History (campaigns) | OK | Scoped by authenticated user |
| Reports | OK | CSV and PDF require authentication |
| Assistant | OK | Templated NLG based on actual run data |
| Frontend routing | OK | No hard route guards; backend enforces auth |
| Frontend API contracts | OK | Axios interceptor attaches Bearer token |
| Backend logs | OK | All endpoints log via `get_logger`; generic exception handler added |
| Production build | PASS | `npm run build` succeeds |
| End-to-end workflow | PASS | Full workflow verified — register, login, dataset, run, endpoints, scenario, reports, assistant, history, isolation, anonymous blocking |

---

## 9. Security Regression

Explicitly verified:
- `anonymous → protected run = 401`
- `anonymous → protected dataset operation = 401`
- `User 2 → User 1 run = 404`
- `User 2 → User 1 dataset = 404`
- `User 2 → User 1 campaign = isolated` (empty list)
- `User 2 → User 1 report = blocked` (404)
- `User 2 → User 1 scenario = blocked` (404)
- `User 2 → User 1 assistant = blocked` (404)

No data leakage.

---

## 10. Files Modified

| File | Change |
|------|--------|
| `app/core/config.py` | Added `app_env` and `__post_init__` JWT validation |
| `app/models/dataset.py` | Added `owner_id` column |
| `app/repositories/dataset_repository.py` | Added `owner_id` to `create`, added `get_owned` and `list_by_owner` |
| `app/services/dataset_service.py` | `create_dataset` accepts `owner_id` |
| `app/services/training_service.py` | Verify dataset ownership before run creation |
| `app/services/confidence_service.py` | **NEW** canonical confidence calculation |
| `app/services/explainability_service.py` | Uses canonical confidence service |
| `app/services/recommendation_service.py` | Uses canonical confidence service |
| `app/api/deps.py` | Removed `get_current_user_optional` |
| `app/api/routes_dataset.py` | `POST /datasets` requires `get_current_user` |
| `README.md` | Updated auth and dataset ownership documentation |
| `AUDIT_REPORT.md` | Updated with final findings and counts |
| `.env.example` | **NEW** environment variable documentation |
| `tests/unit/test_config.py` | **NEW**: 5 JWT config tests |
| `tests/integration/test_ownership.py` | Added 4 dataset ownership tests; updated fixtures |
| `tests/integration/test_recommendation_confidence.py` | Added confidence consistency regression test |
| `tests/integration/test_api.py` | Updated dataset creation to use auth |
| `tests/integration/test_application_audit.py` | Updated dataset creation to use auth |
| `tests/integration/test_campaign_metrics.py` | Updated dataset creation to use auth |
| `scripts/e2e/e2e_verify.py` | Added authenticated dataset creation and ownership checks |

---

## 11. Test Results

```
Tests collected: 181
Tests passed: 181
Tests failed: 0
Tests skipped: 0
Frontend build: PASS
E2E: PASS
Security regression: PASS
Dataset ownership: PASS
JWT configuration: PASS
Confidence consistency: PASS
```

---

## 12. Remaining Limitations

1. **Database migrations** — The project uses `create_all` on startup. Changing the schema (e.g., adding `owner_id`) requires deleting the SQLite file in development. Alembic migrations are not implemented.
2. **Frontend chunk size** — `npm run build` succeeds but emits a chunk size warning (~5 MB JS bundle). Code splitting is not implemented.
3. **Frontend route guards** — `ProtectedRoute` in `App.jsx` redirects unauthenticated users to `/login`. All authorization enforcement is also at the API layer.

---

## 13. Final Verdict

**READY**

All critical security checks pass. The test suite is green (181 passed, 0 failed). The frontend builds successfully. The end-to-end workflow completes without errors. No known blocking security issues remain within the audited application scope.
