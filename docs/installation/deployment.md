# Deployment

## Mandatory Scope: Local Deployment

The mandatory internship deliverable runs entirely locally:

- Backend: `uvicorn app.main:app` on `http://127.0.0.1:8000`
- Frontend: Vite dev server on `http://localhost:5173`
- Database: a local SQLite file, `backend/econocausal.db`, created
  automatically on first startup.

No cloud infrastructure, containers, or CI/CD are required to satisfy
Mid or Final Review.

Docker files were removed from the normal development workflow. The
application runs natively with Python 3.12 + FastAPI on the backend and
Node/Vite on the frontend. If you want to add containerization later,
you can reintroduce Dockerfiles and a `docker-compose.yml`, but it is
not part of the standard local setup.

### Production Build (optional)

To build an optimized production bundle for static hosting:

```bash
cd frontend
npm run build
```

Output is written to `frontend/dist/` (`index.html` + `assets/`).
Serve the built frontend with a static file server (e.g.
`npx serve dist`) and point it at the backend via `VITE_API_BASE_URL`
at build time.

## Optional: Cloud Deployment

Not implemented in this codebase. If attempted, the backend could be
deployed to any Python-friendly host (e.g., a small VM or a managed
container service) and the frontend to a static host, with
`VITE_API_BASE_URL` pointed at the deployed backend URL.
