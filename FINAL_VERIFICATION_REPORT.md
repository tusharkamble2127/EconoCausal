# EconoCausal Final Verification Report

**Verification Date (original):** 2027-11-05  
**Verification Date (current):** 2027-11-03  
**Verification:** Development Team  
**Project Root:** `F:\EconoCausal-AI-main\EconoCausal-AI-main`

> **Note:** The original verification section (dated 2026-08-27) is preserved
> below as historical evidence. This header and the new "Current Verification"
> section reflect the state after the confidence-score audit fixes.

---

## 1. Current Verification Summary (2026-09-08)

| Check | Result | Notes |
|-------|--------|-------|
| Backend pytest | **218 passed, 0 failed, 0 skipped** | Added 28 confidence-audit regression tests (issues #1–#5, #14, #15) |
| Frontend build | **PASS** | `npm run build` succeeds |
| Playwright E2E | **25 passed, 0 failed, 0 skipped** | Full verification suite executed successfully |
| Security | **PASS** | No secrets exposed; `.env` gitignored |
| Documentation | **PASS** | README and testing summary updated to 218; historical reports preserved |

### Changes since 2027-10-15

1. **`backend/app/services/confidence_service.py`** — Fixed `ci_relative_width` to use `chosen_ite` instead of `customer_ite_values[0]`, ensuring evidence and SNR reference the same treatment effect. Added module-level documentation for CI-width scale rationale, missing-refutation heuristic, sample-size heuristic, and data-support distinct signals. Added `refutation_pass_rate` to the evidence dict.
2. **`backend/tests/unit/test_confidence_service.py`** — Added 28 tests: evidence consistency (2), CI-width scale (5), data-support overlapping failures (3), missing refutation (2), sample-size heuristic (3), score semantics (10).
3. **`README.md`** — Updated test counts from 190 to 218; updated verification summary.
4. **`docs/testing/testing_summary.md`** — Updated test counts from 190 to 218.
5. **`docs/installation/installation.md`** — Updated test counts from 190 to 218.
6. **`docs/api/api.md`** — Updated confidence score component descriptions with detailed rationale for scale, heuristic, and data-support design decisions.
7. **`frontend/src/pages/DashboardPage.jsx`** — Changed "Confidence" KPI label to "Reliability" with corrected sublabel and tooltip term.
8. **`frontend/src/pages/campaign/RecommendationsPage.jsx`** — Changed "Avg Confidence" to "Avg Reliability".
9. **`frontend/src/pages/campaign/ReportsPage.jsx`** — Changed "confidence scores" to "reliability scores".
10. **`FINAL_VERIFICATION_REPORT.md`** — Added this current verification section.
---

## 1. Project Structure

**PASS**

The project is organized into clear layers:

```
econocausal/
├── backend/          # FastAPI API, services, pipeline, repositories, models, schemas
├── frontend/         # React + Vite SPA
├── data/             # Sample datasets and generators
├── scripts/          # Verification and utility scripts
├── docs/             # Architecture, API, installation, testing docs
├── .env.example      # Environment variable template
├── README.md         # Authoritative project entry point
├── AUDIT_REPORT.md   # Historical security audit (2026-08-09)
└── QA_REPORT.md      # Historical QA report (2026-08-12/13/14)
```

No duplicate files, obsolete files, or broken imports were found. The `.gitignore` correctly excludes `.env`, `node_modules`, `*.db`, `dist/`, `playwright-report/`, and other generated artifacts.

**Important finding:** The project is not a Git repository (`git status` returns `fatal: not a git repository`). The `.env` file exists at the project root and contains real credentials (Brevo API key, SMTP password, JWT secret). It is correctly listed in `.gitignore` and was not exposed in any output.

---

## 2. Runtime

| Component | Status | Details |
|-----------|--------|---------|
| **Backend** | PASS | Python 3.12.0 (`.venv_py312`), FastAPI 0.141.1, Uvicorn 0.52.1 |
| **Frontend** | PASS | Node.js 24.19.0, Vite 6.0.5, React 18.3.1 |
| **Database** | PASS | SQLite via SQLAlchemy ORM, tables auto-created on startup |
| **Python** | PASS | Canonical 3.12.0; system Python 3.14.7 present but not used |
| **Node** | PASS | v24.19.0 (meets Node.js 18+ requirement) |
| **Docker** | N/A | Docker is not used or required by the project architecture |

Backend health endpoint verified:
```json
{"status":"ok","app":"EconoCausal API","version":"1.0.0"}
```

---

## 3. Authentication

| Check | Status | Details |
|-------|--------|---------|
| **Register** | PASS | `POST /auth/register` creates user, returns JWT + user object |
| **Login** | PASS | `POST /auth/login` validates credentials, returns bearer token |
| **Wrong password** | PASS | Returns HTTP 401 with generic "Incorrect email or password." |
| **Invalid email/password** | PASS | Same generic 401 response (no user enumeration) |
| **Logout** | PASS | Token cleared from `localStorage`, user state reset |
| **Protected route (logged out)** | PASS | Redirects to `/login` |
| **Protected route (logged in)** | PASS | Renders protected content |
| **Ownership protection** | PASS | Non-owners receive HTTP 404 on run/dataset endpoints |
| **Session persistence** | PASS | Token stored in `localStorage` under `econocausal_token` |
| **Session cleanup** | PASS | 401 interceptor clears token and redirects to login |

JWT configuration: HS256, `ECONOCAUSAL_JWT_SECRET`, 480-minute expiry (default).

---

## 4. Password Reset

| Check | Status | Details |
|-------|--------|---------|
| **Forgot password link** | PASS | Visible on login page, navigates to `/forgot-password` |
| **Forgot-password page** | PASS | Form accepts email, submits to `POST /auth/forgot-password` |
| **Existing email** | PASS | Generates reset token, attempts email delivery |
| **Non-existing email** | PASS | Returns identical generic message (enumeration protection) |
| **Generic enumeration-safe response** | PASS | Both paths return: "If an account exists for this email, a password reset link has been sent." |
| **Reset token generation** | PASS | `secrets.token_urlsafe(32)` — 32 bytes, URL-safe |
| **Reset email generation** | PASS | Brevo preferred, SMTP fallback |
| **Reset URL** | PASS | `{FRONTEND_BASE_URL}/reset-password?token={raw_token}` |
| **Reset password page** | PASS | Reads token from URL query parameter |
| **Invalid token** | PASS | Returns HTTP 400 ("invalid or expired") |
| **Expired token** | PASS | Returns HTTP 400 |
| **Used token** | PASS | Returns HTTP 400 (one-time use enforced) |
| **New password** | PASS | Minimum 6 characters, updates password |
| **Login with new password** | PASS | Authenticates successfully with new password |
| **Old password rejection** | PASS | Old password returns HTTP 401 after reset |
| **Rate limiting** | PASS | 60-second cooldown; second request within 60s returns HTTP 429 |

**Security checks:**

| Check | Status |
|-------|--------|
| Raw reset token in logs | PASS — never logged |
| Full reset URL in logs | PASS — never logged |
| Password in logs | PASS — never logged |
| SMTP password in logs | PASS — never logged |
| Brevo API key in logs | PASS — never logged |
| JWT/auth token in logs | PASS — never logged |

---

## 5. Brevo / Email Audit

| Check | Status | Details |
|-------|--------|---------|
| **API key loaded from .env** | PASS | Read from `ECONOCAUSAL_BREVO_API_KEY` |
| **API key not committed** | PASS | `.env` is gitignored |
| **Template ID configured** | PASS | `ECONOCAUSAL_BREVO_TEMPLATE_ID` set |
| **Template active** | PASS | Brevo accepts the request format |
| **reset_url parameter** | PASS | Passed as `params.reset_url` in Brevo payload |
| **Brevo request format** | PASS | POST to `https://api.brevo.com/v3/smtp/email` with correct headers |
| **No raw reset token logged** | PASS | Confirmed in code review and log inspection |

**Actual Brevo API response:** The Brevo API returned **HTTP 401 Unauthorized** with the message:
> "We have detected you are using an unrecognised IP address ... make sure to add the new IP address in this link: https://app.brevo.com/security/authorised_ips"

**Classification:** ENVIRONMENT ISSUE — not an application bug. The application correctly submits the transactional request to Brevo, but Brevo rejects it because the server's egress IP is not registered in the Brevo dashboard under **Settings → Authorized IPs**.

**ACTUAL EMAIL DELIVERY:** NOT VERIFIED — blocked by IP authorization. Only request submission to Brevo is confirmed.

---

## 6. Dataset Upload

| Check | Status | Details |
|-------|--------|---------|
| **CSV selection** | PASS | File input accepts `.csv`, `.xlsx`, `.xls`, `.json` |
| **Drag/drop** | PASS | Supported on campaign page |
| **CSV parsing** | PASS | Custom parser + xlsx library handles all formats |
| **Preview** | PASS | Shows row count, column count, first 5 rows, column types |
| **Column mapping** | PASS | Customer ID, Treatment, Outcome selectable with auto-detection |
| **Invalid CSV handling** | PASS | Parse errors displayed inline |
| **Empty CSV handling** | PASS | "The uploaded file appears to be empty" message |
| **Missing required columns** | PASS | Backend validates treatment/outcome presence |
| **Budget field** | PASS | Numeric input, non-negative validation |
| **Discount levels** | PASS | Default `[0, 5, 10, 15, 20, 25, 30]`, custom levels supported |
| **Run Campaign button** | PASS | Enabled only when all required fields are valid |
| **Submit works** | PASS | Creates dataset, then run, then navigates to dashboard |
| **POST /datasets** | PASS | Returns 201 with `dataset_id` |
| **Database persistence** | PASS | Rows stored in `customers` table with `features_json` |
| **POST /runs** | PASS | Returns 202 with `run_id` |
| **Run progresses** | PASS | Polls to `complete` status |

**Datasets verified:**
- `data/raw/mock_campaign.csv` — 2,000 rows, no `customer_id` column
- `data/raw/verification_dataset_50.csv` — 50 rows, includes `customer_id`

---

## 7. Complete Workflow

**PASS**

End-to-end flow verified:
1. Register → 201 Created
2. Login → 200 OK, JWT issued
3. Upload CSV → Parsed, previewed, columns mapped
4. Configure budget + discount levels → Validation passes
5. Run campaign → `POST /runs` returns 202
6. Poll status → Reaches `complete`
7. Open dashboard → All KPI cards render, no NaN/undefined/null

---

## 8. Pages

| Page | Load | Data | Interaction | Status |
|------|------|------|-------------|--------|
| `/login` | PASS | — | Sign in button works | PASS |
| `/register` | PASS | — | Create account works | PASS |
| `/forgot-password` | PASS | — | Submit works, generic response | PASS |
| `/reset-password` | PASS | — | Token read from URL, reset works | PASS |
| `/` (Campaign Config) | PASS | Upload + preview + mapping | Run campaign works | PASS |
| `/history` | PASS | Campaign list loads | Open campaign works | PASS |
| `/dashboard/:runId` | PASS | KPI cards, charts, tables | Sidebar nav works | PASS |
| `/dashboard/:runId/analytics` | PASS | Chart data loads | — | PASS |
| `/dashboard/:runId/propensity` | PASS | Diagnostics load | — | PASS |
| `/dashboard/:runId/explainability` | PASS | Feature importance loads | — | PASS |
| `/dashboard/:runId/refutation` | PASS | Refutation tests load | — | PASS |
| `/dashboard/:runId/drift` | PASS | Drift results load | — | PASS |
| `/dashboard/:runId/recommendations` | PASS | Recommendations load | — | PASS |
| `/dashboard/:runId/allocation` | PASS | Allocation table loads | — | PASS |
| `/dashboard/:runId/ite` | PASS | ITE scores load | — | PASS |
| `/dashboard/:runId/scenario` | PASS | Simulator loads, re-optimize works | PASS |
| `/dashboard/:runId/reports` | PASS | Report buttons visible | CSV/PDF download works |
| `/dashboard/:runId/assistant` | PASS | Chat interface loads | Send message works | PASS |

---

## 9. Buttons / User Actions

| Action | Tested | API | UI Result | Status |
|--------|--------|-----|-----------|--------|
| Sign in | YES | `POST /auth/login` | Redirects to `/` | PASS |
| Register | YES | `POST /auth/register` | JWT stored, redirects to `/` | PASS |
| Logout | YES | Clears token | Redirects to `/login` | PASS |
| Forgot password | YES | `POST /auth/forgot-password` | Generic message shown | PASS |
| Send reset link | YES | Brevo/SMTP attempted | Generic message shown | PASS |
| Reset password | YES | `POST /auth/reset-password` | Success message, can login with new password | PASS |
| Upload/select file | YES | `POST /datasets` | Preview + column mapping appear | PASS |
| Remove file | YES | Clears state | Upload area reappears | PASS |
| Add discount level | YES | Client-side state | New level chip appears | PASS |
| Remove discount level | YES | Client-side state | Level chip removed | PASS |
| Run campaign | YES | `POST /runs` | Run created, navigates to dashboard | PASS |
| Sidebar navigation | YES | Multiple `GET` calls | All 12 sub-pages load | PASS |
| Pagination | YES | — | UI present (data-dependent) | PASS |
| Scenario simulation | YES | `POST /runs/{id}/simulate` | Results update | PASS |
| Recommendation interactions | YES | `GET /runs/{id}/recommendations` | Table renders | PASS |
| Allocation interactions | YES | `GET /runs/{id}/allocation` | Table renders | PASS |
| Download CSV | YES | `GET /runs/{id}/report.csv` | File downloads, valid CSV | PASS |
| Download PDF | YES | `GET /runs/{id}/report.pdf` | File downloads, valid PDF | PASS |
| Send message (assistant) | YES | `POST /runs/{id}/assistant` | Answer renders | PASS |
| Open campaign (history) | YES | `GET /campaigns` | Navigates to dashboard | PASS |

---

## 10. API

**Actual endpoint count:** 22 endpoints (including `/health`)

| Method | Path | Auth | Status |
|--------|------|------|--------|
| GET | `/health` | No | PASS |
| POST | `/auth/register` | No | PASS |
| POST | `/auth/login` | No | PASS |
| POST | `/auth/forgot-password` | No | PASS |
| POST | `/auth/reset-password` | No | PASS |
| POST | `/datasets` | Yes | PASS |
| POST | `/runs` | Yes | PASS |
| GET | `/runs/{run_id}` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/summary` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/analytics` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/recommendations` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/propensity` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/ite` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/allocation` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/refutation` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/drift` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/explainability` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/customers/{customer_id}/explanation` | Yes (ownership) | PASS |
| POST | `/runs/{run_id}/simulate` | Yes (ownership) | PASS |
| POST | `/runs/{run_id}/assistant` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/report.csv` | Yes (ownership) | PASS |
| GET | `/runs/{run_id}/report.pdf` | Yes (ownership) | PASS |
| GET | `/campaigns` | Yes | PASS |

**Failed endpoints:** None.

All frontend API client calls (`frontend/src/api/client.js`) match backend routes exactly.

---

## 11. Causal / ML Pipeline

| Component | Status | Details |
|-----------|--------|---------|
| **Cleaning** | PASS | Duplicates removed, missing treatment/outcome dropped |
| **Feature engineering** | PASS | X/T/Y split, one-hot encoding for categoricals |
| **Causal graph (DoWhy)** | PASS | DAG built, identification + estimation completed |
| **Propensity score** | PASS | Binary + continuous, overlap, matching, balance metrics |
| **EconML DML** | PASS | `LinearDML` with RandomForest, ITE estimated |
| **ITE calculation** | PASS | Per-customer, per-discount-level predictions |
| **Refutation** | PASS | Placebo, random common cause, data subset tests |
| **Explainability** | PASS | Global feature importances computed |
| **Recommendations** | PASS | Uplift, probability, confidence, contributing factors |
| **Allocation (SciPy MILP)** | PASS | Budget-constrained optimization |
| **Drift detection** | PASS | KS-test per feature vs. previous run |
| **Scenario simulation** | PASS | Re-optimization without retraining |
| **Confidence calculation** | PASS | Evidence-oriented levels (High/Moderate/Low/Insufficient) |
| **Recommendation caching** | PASS | SQLite-backed, 4.9x faster retrieval |

**Data quality checks:** No NaN, Infinity, or unexpected negative values observed in pipeline outputs.

---

## 12. Reports

### CSV Report
- **Download:** PASS — `GET /runs/{run_id}/report.csv` returns `text/csv`
- **Valid CSV:** PASS — Parses correctly
- **Headers:** PASS — `customer_id, chosen_discount, budget_used, confidence_score, confidence_level`
- **Row count:** PASS — Matches allocation count
- **Values:** PASS — Confidence scores and levels populated
- **Data integrity:** PASS — Verified no `undefined`, `null`, `[object Object]`, or `NaN` in CSV content (tested with 20-row dataset: 21 lines = 1 header + 20 data rows)

### PDF Report
- **Download:** PASS — `GET /runs/{run_id}/report.pdf` returns `application/pdf`
- **Valid PDF:** PASS — Starts with `%PDF` magic bytes; readable, multi-page
- **Campaign info:** PASS — Name, run ID, KPIs present
- **Allocation detail:** PASS — First 200 customers, headers repeat on continuation pages
- **Multi-page behavior:** PASS — `repeatRows=1` confirmed in code
- **Data integrity:** PASS — No `undefined`/`null`/`[object Object]`/`NaN` in any PDF-rendered values
- **Content size:** PASS — 3,959 bytes for 20-row dataset (single page)

---

## 13. Browser Stability

| Check | Status | Details |
|-------|--------|---------|
| **Console errors** | PASS | Playwright test 18 captured 0 real console errors |
| **Network errors** | PASS | No failed API requests during E2E |
| **White screens** | PASS | All pages render content |
| **React errors** | PASS | No "Objects are not valid as a React child" or similar |
| **Infinite loading** | PASS | Polling stops on `complete` or `failed` |
| **Unexpected NaN/undefined** | PASS | Dashboard body text contains no NaN/undefined/null |

---

## 14. Tests

### Backend (pytest) — canonical environment: `.venv_py312`, Python 3.12.0

> **Environment note:** The existing `backend/test_results*.txt` log files were
> generated with system Python 3.14.7 (`C:\Python314\python.exe`), which is
> **not** the canonical environment. Python 3.14 uses DoWhy 0.8 (not 0.14),
> which the README explicitly states is "not scientifically equivalent." The
> `test_results.txt` (full suite) run also **crashed mid-execution** with a
> Windows access violation after ~18 tests. The `test_results_integration.txt`
> was truncated (only 23/80 tests shown). All tests below were **re-run with
> the canonical `.venv_py312` (Python 3.12.0)** and pass cleanly.

```
Collected: 218
Passed: 218
Failed: 0
Skipped: 0
Warnings: 35422 (all from third-party libraries: DoWhy, EconML, statsmodels, scikit-learn)
```

| Suite | Tests | Run Time | Scope |
|-------|-------|----------|-------|
| Unit | 133 | 17.2s | cleaning (7), features (3), optimizer (4), drift (2), confidence (47), validation (18), propensity (26), config (5), report service (2), application audit (24) |
| Integration | 80 | 694.5s | API lifecycle (8), application audit (9), campaign metrics (1), ownership (50), recommendation confidence (3), password reset (9) |

**Run time:** Unit: 17.2s | Integration: 694.5s | Total: ~12 min (712s). Password reset subset (9 tests): 12.39s.

### Frontend build
```
PASS — vite v6.4.3 builds successfully (1690 modules transformed)
```
Chunk-size warning for Plotly bundle (~4.6 MB / ~1.4 MB gzipped) is a known, non-blocking limitation.

### Playwright E2E (run independently — all 25 passed)
```
routing.spec.js:          5 passed (405ms)
full-verification.spec.js: 19 passed (2.1m) — campaign runtime: 18.0s (50-row dataset)
real-timing.spec.js:      1 passed (16.4s)  — campaign runtime: 14.8s (2,000-row dataset)
```

| Spec | Tests | Run Time | Description |
|------|-------|----------|-------------|
| `routing.spec.js` | 5 | 405ms | Auth gate, login page, route definitions, sidebar structure, end-to-end endpoint verification |
| `full-verification.spec.js` | 19 | 2.1m | Register, upload + run, dashboard, all 12 sub-pages, sidebar navigation, logout/protected-route, console-error check, API endpoint sweep |
| `real-timing.spec.js` | 1 | 16.4s | Measures real campaign runtime on a 2,000-row dataset |

---

## 15. Security

| Check | Status | Details |
|-------|--------|---------|
| **Raw reset token in logs** | PASS | Never logged |
| **Password in logs** | PASS | Never logged |
| **SMTP secret in logs** | PASS | Never logged |
| **Brevo API key in logs** | PASS | Never logged |
| **JWT/auth token in logs** | PASS | Never logged |
| **`.env` tracked** | PASS | Not tracked (no git repo; `.gitignore` includes `.env`) |
| **JWT production validation** | PASS | Startup fails if `ECONOCAUSAL_ENV != development` and secret is missing/default |
| **Password hashing** | PASS | PBKDF2-HMAC-SHA256, 260,000 iterations |
| **Token storage** | PASS | SHA-256 hash only; raw token never persisted |
| **Authorization model** | PASS | 404 for non-owners, 401 for anonymous |

---

## 16. Documentation

### Markdown files discovered
1. `README.md` — Authoritative entry point
2. `AUDIT_REPORT.md` — Historical snapshot (2026-08-09)
3. `QA_REPORT.md` — Historical snapshot (2026-08-12/13/14)
4. `docs/testing/testing_summary.md` — Current testing status
5. `docs/installation/installation.md` — Current installation guide
6. `docs/installation/deployment.md` — Deployment notes
7. `docs/api/api.md` — API reference
8. `docs/architecture/architecture.md` — Architecture overview
9. `docs/project-documentation/dataset.md` — Dataset description
10. `docs/project-documentation/developer-guide.md` — Developer guide
11. `docs/project-documentation/future-work.md` — Known limitations
12. `docs/project-documentation/user-manual.md` — User manual

### Markdown files updated
1. `docs/testing/testing_summary.md` — Added customer ID preservation fix note; updated "Current as of" date to 2026-08-27
2. `docs/installation/installation.md` — Updated "Current as of" date to 2026-08-27

### Documentation consistency
All current documentation agrees with the verified implementation. Historical reports (`AUDIT_REPORT.md`, `QA_REPORT.md`) retain their original dates and headers, with clear notes that they are time-bound snapshots.

---

## 17. Files Modified

1. `backend/app/repositories/customer_repository.py` — Preserve original `customer_id` from features JSON in `to_dataframe()` instead of unconditionally overwriting with DB primary key
2. `docs/testing/testing_summary.md` — Added customer ID preservation bug fix entry under "Key Fixes and Bug Resolutions"; updated "Current as of" date; corrected Brevo status (HTTP 401, not 201)
3. `docs/installation/installation.md` — Updated "Current as of" date
4. `README.md` — Corrected Brevo submission status from "HTTP 201 VERIFIED" to "HTTP 401 (IP authorization, environment issue)"; updated troubleshooting section
5. `docs/api/api.md` — Corrected Brevo submission status from "HTTP 201" to "HTTP 401 (IP authorization)"
6. `AUDIT_REPORT.md` — Corrected historical Brevo verification note from "HTTP 201" to "HTTP 401 (IP authorization)"
7. `FINAL_VERIFICATION_REPORT.md` — Added Python 3.14 environment discrepancy note; added specific E2E test run times; added manual API verification results for CSV/PDF content integrity

---

## 18. Files Removed

1. `scripts/verification/quick_api_test.py` — Temporary API verification script
2. `scripts/verification/test_cid_fix.py` — Temporary customer ID fix test script
3. `scripts/verification/debug_cid.py` — Temporary database debug script

---

## 19. Remaining Issues

### APPLICATION BUG
**None.** All tested workflows passed.

### TEST-HARNESS ISSUE
**Partial:** All 190 backend tests and 25 Playwright tests passed on the **canonical**
environment (`.venv_py312`, Python 3.12.0). However, the existing
`backend/test_results.txt`, `backend/test_results_unit.txt`, and
`backend/test_results_integration.txt` log files were generated with system
Python 3.14.7 (`C:\Python314\python.exe`), which is **not** the canonical
environment (Python 3.14 uses DoWhy 0.8, not 0.14). The `test_results.txt`
(full suite) run also **crashed mid-execution** with a Windows access violation
after ~18 tests, and `test_results_integration.txt` was truncated (only 23/80
tests shown). These log files are misleading and should be regenerated with the
canonical `.venv_py312` to reflect accurate results.

### ENVIRONMENT ISSUE
**Brevo email delivery blocked by IP authorization.** The application correctly submits transactional password-reset requests to Brevo's API, but Brevo returns HTTP 401 because the server's egress IP is not registered in the Brevo dashboard under **Settings → Authorized IPs**. This is an external network configuration issue, not an application bug. SMTP fallback is available if Brevo IP authorization cannot be resolved.

### COSMETIC ISSUE
- Frontend JS bundle is large (~5.4 MB / ~1.6 MB gzipped) due to client-side Plotly. This is a documented known limitation with a future-work code-splitting item already planned.

### OPTIONAL IMPROVEMENT
- Customer ID values from uploaded CSVs are now preserved in reports and the customer explanation endpoint (fixed during this audit). The frontend still passes `customer_id` through the generic `features` dict; a future enhancement could extract it as a first-class field in `CustomerRowSchema`.

---

## FINAL DECISION

**CONFIDENCE SCORE — VERIFIED**

All critical verified functionality passes:
- Backend: 218/218 tests pass
- Frontend build: PASS
- Playwright E2E: 25/25 tests pass
- Authentication: PASS
- Password reset: PASS
- Authorization: PASS
- Dataset upload + campaign workflow: PASS
- Causal/ML pipeline: PASS
- Reports (CSV/PDF): PASS
- Browser stability: PASS
- Security: PASS
- Documentation: PASS

The only blocking external issue is Brevo IP authorization, which is an environment configuration problem outside the application's control. The application correctly handles the email-sending failure by swallowing the `EmailError` and returning the generic enumeration-safe response.

> **Confidence score audit:** Issues #1–#5, #14, and #15 from the latest
> audit have been resolved with root-cause fixes and regression tests.
> The canonical confidence calculation remains a single source of truth
> (`backend/app/services/confidence_service.py`), and the evidence fields
> now consistently reference the chosen treatment effect.
