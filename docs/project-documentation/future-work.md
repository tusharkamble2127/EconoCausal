# Future Work / Known Limitations

## Implemented (No Longer Pending)

- **Recommendation caching:** SQLite-backed persistence of precomputed
  recommendations, yielding **4.9x faster** response on the
  `/runs/{run_id}/recommendations` endpoint (1.36s → 0.28s on a 1,500-customer
  dataset with 7 discount levels). Cached rows are written during the
  `recommendation_cache` pipeline stage that runs after a run completes;
  older uncached runs fall back to on-demand computation. See
  `docs/architecture/architecture.md` and `app/services/confidence_service.py`.
- **White-screen bug fixes:** React hook-ordering violation in
  `DashboardPage.jsx` and missing `InfoTooltip` import were found and fixed
  (see `docs/testing/testing_summary.md` and `QA_REPORT.md` for the forensic
  investigation).
- **Infinite polling fix:** `useRun` hook no longer loops indefinitely on
  404 errors.

## Known Limitations

- The causal DAG's confounder set is limited to whatever columns are
  present in the uploaded dataset; an unobserved confounder not captured
  in the data cannot be adjusted for. This is a general limitation of
  observational causal inference, not specific to this implementation.
- Training runs synchronously within the API request; a very large dataset
  could make a single `/runs` call slow. The Axios client timeout is set to
  **600 seconds** (600000 ms) to accommodate this; a background task queue
  would be the natural next step for sub-second response times.
- The optimizer currently supports a discrete, small set of candidate
  discount levels (`settings.candidate_discount_levels`); extending to a
  continuous discount range would require a different (non-MILP)
  optimization formulation.
- The AI assistant uses deterministic templated natural-language generation
  rather than an external LLM. It is designed to be swappable behind the
  same `/runs/{id}/assistant` endpoint.
- Frontend route guards exist (`ProtectedRoute` in `App.jsx`) but are
  limited; all authorization enforcement is at the API layer.

## Optional Enhancements Not Implemented

- Model registry and experiment tracking
- A/B testing framework integration
- Dark mode
- Usage analytics
- Code splitting and lazy loading for frontend routes and heavy chart libraries (Plotly)
- PostgreSQL migration with Alembic versioning
- Background task queue (Celery / ARQ) for long-running pipeline executions
- Role-based access control beyond ownership checks
- Real LLM backend for the assistant endpoint

None of the above are required by the Infotact internship deliverable.
