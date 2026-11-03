# EconoCausal Project Testing Summary

> **Current as of:** 2026-08-27. Verified against the canonical environment
> (`backend/.venv_py312`, Python 3.12.0). See `../README.md` at the project
> root for the authoritative status. Historical audit reports
> (`../../AUDIT_REPORT.md`, `../../QA_REPORT.md`) are preserved as dated
> snapshots at earlier points in the project timeline.

## Environment

- **Backend Python:** 3.12.0 (canonical), with pinned dependencies in
  `backend/requirements.txt` and a pre-built virtual environment at
  `backend/.venv_py312`
- **Backend:** http://127.0.0.1:8000
- **Frontend:** http://localhost:5173
- **Database:** SQLite (`backend/econocausal.db`)
- **Auth:** JWT Bearer tokens (HS256, PBKDF2-HMAC-SHA256 password hashing)

### Canonical dependency versions

| Technology | Version |
|------------|---------|
| Python | 3.12.0 |
| FastAPI | 0.141.1 |
| Uvicorn | 0.52.1 |
| Pydantic | 2.13.4 |
| SQLAlchemy | 2.0.51 |
| Pandas | 3.0.2 |
| NumPy | 2.4.4 |
| SciPy | 1.15.3 |
| Scikit-learn | 1.8.0 |
| DoWhy | 0.14 |
| EconML | 0.17.0 |
| HTTPX | 0.28.1 |
| PyJWT | 2.7.0 |
| ReportLab | 4.4.10 |
| email-validator | 2.2.0 |
| Pytest | 9.1.1 |

---

## Current Verification Results

| Check | Result | How |
|-------|--------|-----|
| Backend pytest | **218 passed, 0 failed, 0 skipped** | `.venv_py312` (Python 3.12.0, canonical pins) |
| Playwright E2E | **25 passed, 0 failed, 0 skipped** (5 + 19 + 1) | Chromium, both servers running |
| Frontend build | **PASS** | `npm run build` (1690 modules transformed) |
| Health endpoint | **PASS** | `/health` returns `{"status":"ok"}` |
| Auth (register/login) | **PASS** | JWT issued, PBKDF2 password verification |
| Password reset | **PASS** | 9 integration tests; Brevo/SMTP submission attempted (HTTP 401 due to IP authorization — environment issue, handled gracefully) |
| Authorization | **PASS** | 404 on non-owner, 401 anonymous |
| Brevo API submission | **ATTEMPTED — HTTP 401** | Request format correct; Brevo rejects IP authorization (environment issue). Application catches `EmailError` and returns generic response. |
| Brevo inbox delivery | **Not verified** | Blocked by Brevo IP authorization; SMTP fallback available |
| Password-reset security | **PASS** | secrets.token_urlsafe(32), SHA-256 hash storage, 30-min expiry, 60s rate limit, single-use, enumeration protection, old-password rejection, weak-password 422 |

## Backend Tests (pytest)

```bash
cd backend
PYTHONPATH=. python -m pytest tests/ -v
```

| Suite | Tests | Scope |
|-------|-------|-------|
| Unit | 133 | cleaning (7), features (3), optimizer (4), drift (2), confidence (47), validation (18), propensity (26), config (5), report service (2), application audit (24) |
| Integration | 80 | API lifecycle (8), application audit (9), campaign metrics (1), ownership (50), recommendation confidence (3), **password reset (9)** |
| **Total** | **218** | **218 passed, 0 failed, 0 skipped** |

The 9 password-reset integration tests cover: generic response for
nonexistent email, generic response for existing user, email-format
validation, 60-second rate limiting, successful reset flow, login after reset
with old-password rejection, invalid token, weak password (422), and one-time
use enforcement.

**Verified environment:** Python 3.12.0 with canonical pinned dependencies
located in `backend/.venv_py312`. Full suite run time ~12 minutes (integration
tests execute the full causal pipeline).

## Playwright E2E Tests (browser)

Three spec files in `frontend/tests/`, **25 tests total — 25 passed, 0 failed,
0 skipped.**

| Spec | Tests | Description |
|------|-------|-------------|
| `routing.spec.js` | 5 | Auth gate, login page, route definitions, sidebar structure, end-to-end endpoint verification |
| `full-verification.spec.js` | 19 | Full browser audit: register, upload + run, dashboard, all 12 dashboard sub-pages, sidebar navigation, logout/protected-route, console-error check, and a full API endpoint sweep |
| `real-timing.spec.js` | 1 | Measures real campaign runtime on a 2,000-row dataset |

**Requirements:** both the backend (`http://127.0.0.1:8000`) and the frontend
dev server (`http://localhost:5173`) must be running, and Chromium must be
installed (`npx playwright install`).

```bash
cd frontend
npx playwright test --reporter=list --workers=1
```

## Playwright E2E Strategy (condition-based polling)

The `full-verification.spec.js` redesign replaced a brittle fixed-URL wait
with **condition-based campaign-state polling**:

1. **Campaign discovery:** After submitting a run, the test polls
   `GET /campaigns` (owner-scoped) and matches on `campaign_name` to locate
   the new run ID.
2. **Run discovery:** The matched `run_id` is extracted from campaign history.
3. **State polling:** `GET /runs/{run_id}` is polled directly against the API
   at a **5-second interval** (up to 180 polls = 15 minutes of wall-clock
   budget).
4. **Explicit state handling:** The loop inspects `status` and branches on
   `complete` (proceed to dashboard verification), `failed` (fail the test),
   and `running`/other (keep polling).
5. **Transient-error retries:** Network failures on the status fetch are
   retried up to 3 times inside the polling loop before propagating.
6. **Diagnostic logging:** The run ID and a periodic status log
   (`Campaign {runId} poll {i}: status=...`) are emitted so a stall is
   diagnosable in CI output.
7. **Timeout diagnostics:** If the campaign does not complete, the thrown
   error includes elapsed time and the last observed status, pointing the
   operator to backend logs.
8. **Final dashboard verification:** After `complete`, the test navigates to
   the dashboard and asserts KPI cards render with no `NaN`/`undefined`/`null`
   leakage.

### Timeout configuration

| Component | Timeout | Source |
|-----------|---------|--------|
| Axios client | **600 seconds** (600000 ms) | `frontend/src/api/client.js` |
| Playwright global | **600 seconds** (600000 ms) | `frontend/playwright.config.ts` |
| Full-verification campaign test | **900 seconds** (900000 ms) | `test.setTimeout(900000)` in `full-verification.spec.js` |

The Playwright global timeout governs the overall test suite. The campaign
test sets a 900-second timeout via `test.describe.configure({ mode: 'serial' })`
to bound the overall campaign wait. The polling polls the API directly (via
`page.request`), which uses its own fetch rather than the browser's Axios
instance, so it is not constrained by the 600-second Axios timeout.

## Frontend Build

```bash
cd frontend
npm run build
```

**PASS** — `vite v6.4.3` builds successfully (1690 modules transformed). The
build emits a chunk-size warning because the JS bundle is large (~5.4 MB /
~1.6 MB gzipped) due to client-side Plotly. This is a known, non-blocking
limitation (see `../project-documentation/future-work.md`).

## Key Fixes and Bug Resolutions

### White Screen Bugs (fixed)

Two critical runtime bugs in `DashboardPage.jsx` caused a white/blank screen
when navigating to any dashboard page after a run completed:

1. **React Hook Ordering Violation:** `useMemo` was called conditionally
   after three early-return guard clauses. Fixed by moving `useMemo` before
   the early returns so it is always called on every render.
   - **File:** `frontend/src/pages/DashboardPage.jsx`
   - **Regression:** 10-row and 1,500-row dataset workflows both PASS; all
     16 dashboard sub-pages render correctly; no console errors.

2. **Missing `InfoTooltip` Import:** `DashboardPage.jsx` used `<InfoTooltip>`
   in 6 KPI card tooltips but never imported the component. Fixed by adding
   the import.
   - **File:** `frontend/src/pages/DashboardPage.jsx`
   - **Regression:** All KPI card tooltips render and are clickable; no
     console errors.

### Infinite Polling Bug (fixed)

**File:** `frontend/src/hooks/useRun.js`

**Problem:** When navigating to a non-existent run (404), the `useRun` hook
entered an infinite polling loop. The `setInterval` checked
`statusRef.current` to determine when to stop polling, but when `getRun()`
failed in the `catch` block, `statusRef.current` was never updated from
`null`.

**Fix:** Added `statusRef.current = "failed"` in the `catch` block so the
interval clears on the next tick.

**Verification:** Navigated to `/dashboard/99999`. Console errors stopped at
2 (initial request only). No further API calls made after 5 seconds of
observation.

### Customer ID Preservation Bug (fixed)

**File:** `backend/app/repositories/customer_repository.py`

**Problem:** When a CSV contained a `customer_id` column, `to_dataframe()` unconditionally overwrote it with the database auto-increment primary key. This caused the original customer identifiers from uploaded datasets to be lost in reports and the customer explanation endpoint.

**Fix:** Changed `to_dataframe()` to preserve the original `customer_id` from the stored features JSON when present, falling back to the database primary key only when no `customer_id` exists in the features.

**Verification:** Created a dataset with explicit `customer_id` values (1, 2, 3), ran the pipeline, and confirmed the ITE scores and customer explanation endpoint now return the original identifiers. All 218 backend tests continue to pass.

### Test Harness Issues (historical, not application bugs)

The early iterations of the Playwright debug tests had harness-specific
issues that have since been resolved:

- **`routing.spec.js` (historical 3/5):** Early versions used hardcoded test
  emails (`playwright3@test.com`, `routingtest@test.com`) that persisted
  across runs and caused 2 failures. The current version uses
  timestamped emails and passes 5/5.
- **`debug-test2.spec.js`:** A debug test with a non-standard selector that
  timed out on `page.selectOption`. This was a debug-only test, not part of
  the primary E2E suite.

These are noted for historical context only; the primary E2E suite
(`full-verification.spec.js`, `routing.spec.js`, `real-timing.spec.js`) passes
25/25.

## Critical Context

- Frontend route guards are enforced at the API layer; `ProtectedRoute` in
  `App.jsx` provides additional frontend-level protection.
- Large JS bundle (~5.4 MB) due to Plotly bundled client-side.
- Backend uses environment-validated JWT secret (`ECONOCAUSAL_JWT_SECRET`
  required in production; fails fast at startup if missing or default).
- The underlying estimator is configured internally (`RandomForest`) inside
  EconML's `LinearDML`; users do not select or switch models through the
  frontend.
- Recommendation caching (SQLite-backed) was introduced, yielding 4.9x
  faster response on the `/recommendations` endpoint (1.36s → 0.28s on a
  1,500-customer dataset).
- No linting/typecheck tools are configured (no ruff, mypy, pyproject.toml,
  or type-checker config in the project).

## Current Status

| Area | Status |
|------|--------|
| Backend tests (218) | PASS |
| Playwright E2E (25) | PASS |
| Frontend build | PASS |
| Authentication | PASS |
| Password Reset | PASS |
| Authorization | PASS |
| Dataset ownership | PASS |
| Causal pipeline | PASS |
| Recommendations (cached) | PASS |
| Explainability | PASS |
| Scenario simulation | PASS |
| Reports (CSV/PDF) | PASS |
