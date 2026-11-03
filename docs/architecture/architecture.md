# Architecture

See Volume I Chapter 3 and Volume II Chapter 1 for the full narrative and
Mermaid diagrams (high-level architecture, frontend/backend architecture,
ML pipeline, database architecture, REST API architecture, component
diagram, sequence diagram, data flow diagram, deployment diagram).

## Causal DAG

Nodes: confounders (from `pipeline/features.py::engineer`), `treatment`
(discount amount), `outcome` (purchase/stay). Edges: confounders ->
treatment, confounders -> outcome, treatment -> outcome. Built in
`pipeline/causal_graph.py::build_model`.

## Base Estimator

The underlying estimator is configured internally as RandomForest (via
`scikit-learn`'s `RandomForestRegressor`) inside EconML's `LinearDML`
(see `pipeline/dml_model.py`). Users do not select or switch models
through the frontend. The backend API schema accepts `base_estimator`
for completeness, but only `RandomForest` is currently supported.

## Optimizer Formulation

Binary decision variables `x[i, k]` (customer i receives discount level
k). Objective: maximize total ITE-weighted uplift. Constraints: exactly
one discount level per customer; total spend <= budget. Solved as a
linear MILP via `scipy.optimize.milp` (see `pipeline/optimizer.py`).

## Drift Detection Method

Two-sample Kolmogorov-Smirnov test per numeric confounder, comparing the
training data's distribution to newly submitted data's distribution.
A feature is flagged as drifted when the KS test's p-value falls below
`settings.drift_p_value_threshold` (default 0.05). See
`pipeline/drift_detector.py`.

## Recommendation Cache

The `/runs/{run_id}/recommendations` endpoint uses SQLite-backed result
persistence to avoid recomputing recommendations on every request:

1. Run completes → pipeline computes recommendations once during
   `recommendation_cache` stage.
2. Results are persisted to `recommendation_results` table with
   JSON-serialized confidence intervals, evidence, and contributing
   factors.
3. Subsequent `GET /runs/{id}/recommendations` returns cached rows
   directly (no DataFrame reconstruction or feature engineering).
4. If no cache exists (e.g., older runs), the endpoint falls back to
   on-demand computation.

Verified improvement: 4.9x faster (1.362s → 0.279s) on a 1,500-customer
dataset with 7 discount levels.

## Performance Notes

The optimizer was validated on a 1500-row synthetic dataset
(`data/generators/generate_mock_data.py`) with 3 discount levels (4500 decision
variables) and solves in well under a second locally via the HiGHS
solver backing `scipy.optimize.milp`.

Dashboard concurrent load (9 parallel requests) improved from 2.880s to
2.609s (~9% faster) after recommendation caching was introduced.
