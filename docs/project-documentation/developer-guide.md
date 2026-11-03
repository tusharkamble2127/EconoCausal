# Developer Guide

See Volume II Chapter 2 for the full folder-by-folder rationale and
Chapter 6 for coding standards.

## Adding a New Pipeline Stage

1. Create `backend/app/pipeline/<stage_name>.py` with a module-level
   docstring explaining its role in the overall pipeline.
2. Add type-hinted, docstring-documented functions — no FastAPI imports
   allowed in this layer (pipeline/ must remain framework-independent).
3. Add a unit test in `backend/tests/unit/test_<stage_name>.py`.
4. Wire the stage into `app/services/training_service.py`'s
   `create_run()` sequence, in the correct pipeline order (Volume I
   Chapter 8).

## Adding a New Endpoint

1. Add a Pydantic request/response schema in `app/schemas/`.
2. Add a service function in `app/services/` containing the business
   logic — never put logic directly in a route function.
3. Add a repository function in `app/repositories/` if new data access
   is needed — services never query the database directly.
4. Add the route in `app/api/routes_<name>.py` and register the router
   in `app/main.py`.
5. Add an integration test in `backend/tests/integration/test_api.py`.

## Adding a New Frontend Component

1. Create `frontend/src/components/<Name>.jsx` (PascalCase, one
   component per file).
2. Keep it presentational — accept data via props; do not call the API
   client directly from inside a component if a page/hook already fetches
   the data (Volume II Chapter 1.2).
3. Use Tailwind utility classes matching the color palette in Volume II
   Chapter 9.7.

## Running the Full Stack Locally

See `../installation/installation.md`.
