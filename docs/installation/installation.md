# Installation Guide

> **Current as of:** 2026-08-27. Verified against the canonical environment
> (`backend/.venv_py312`, Python 3.12.0). See `../README.md` at the project root
> for the authoritative entry point.

## Prerequisites

- Python 3.12 (matches `.python-version`; the provided `backend/.venv_py312`
  pre-built virtual environment already satisfies this)
- Node.js 18+
- Git

## Backend

### Option A: Use the pre-built virtual environment (recommended)

A pre-built Python 3.12 virtual environment with all pinned dependencies is
provided at `backend/.venv_py312`:

```bash
cd backend
.venv_py312\Scripts\activate      # Windows
# source .venv_py312/bin/activate  # macOS/Linux
python -m uvicorn app.main:app --reload --env-file "../.env"
```

### Option B: Create a fresh environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --env-file "../.env"
```

The API starts at `http://127.0.0.1:8000`. On first startup, all database
tables are created automatically in `backend/econocausal.db` (SQLite) — no
manual migration step is required (the project uses
`Base.metadata.create_all` on startup; Alembic migrations are not configured).

> **Environment file:** The `--env-file "../.env"` flag points the backend at
> the root `.env`. All `ECONOCAUSAL_*` variables are read from there. Copy
> `.env.example` to `.env` and fill in real values. Never commit `.env`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard starts at `http://localhost:5173` and calls the backend at
`http://127.0.0.1:8000` by default (override with the `VITE_API_BASE_URL`
environment variable if needed).

## Running Tests

### Backend (pytest)

```bash
cd backend
PYTHONPATH=. python -m pytest tests/ -v
```

| Suite | Tests | Scope |
|-------|-------|-------|
| Unit | 133 | cleaning (7), features (3), optimizer (4), drift (2), confidence (47), validation (18), propensity (26), config (5), report service (2), application audit (24) |
| Integration | 80 | API lifecycle (8), application audit (9), campaign metrics (1), ownership (50), recommendation confidence (3), password reset (9) |
| **Total** | **218** | **218 passed, 0 failed, 0 skipped** |

> **Password reset tests:** The 9 password-reset integration tests cover:
> generic response for nonexistent email, generic response for existing user,
> email-format validation, 60-second rate limiting, successful reset flow,
> login after reset with old-password rejection, invalid token, weak password
> (422), and one-time use enforcement.

**Verified environment:** Python 3.12.0 with canonical pinned dependencies
located in `backend/.venv_py312`. Full suite run time ~12 minutes (integration
tests execute the full causal pipeline).

### Playwright E2E (browser)

Three spec files in `frontend/tests/`, **25 tests total — 25 passed, 0 failed,
0 skipped** (5 + 19 + 1).

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

### Playwright E2E Strategy (condition-based polling)

The `full-verification.spec.js` uses **condition-based campaign-state polling**
instead of a brittle fixed-URL wait:

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
   diagnosable.
7. **Timeout diagnostics:** If the campaign does not complete, the thrown
   error includes elapsed time and the last observed status.

**Timeouts:** The Axios client timeout is **600 seconds**
(`frontend/src/api/client.js`). The Playwright global timeout is **600
seconds** (`playwright.config.ts`). The campaign test in
`full-verification.spec.js` sets `test.setTimeout(900000)` (900 seconds / 15
minutes) via `test.describe.configure({ mode: 'serial' })` to bound the
overall campaign wait. The polling polls the API directly (via
`page.request`), which uses its own fetch rather than the browser's Axios
instance, so it is not constrained by the Axios timeout.

### Generating a Fresh Mock Dataset

```bash
cd data
python generators/generate_mock_data.py --n 2000 --out raw/mock_campaign.csv
```
