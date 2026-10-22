"""
FastAPI application entry point (Volume II Chapter 10.1, Chapter 10.6).

Creates the app, configures CORS for the Vite dev server, registers all
routers, registers the global exception handler that converts every
EconoCausalError subclass into the standard error envelope (Volume II
Chapter 7.7), and initializes the database on startup.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_allocation,
    routes_analytics,
    routes_assistant,
    routes_auth,
    routes_dataset,
    routes_drift,
    routes_explainability,
    routes_history,
    routes_ite,
    routes_propensity,
    routes_recommendation,
    routes_refutation,
    routes_report,
    routes_run,
    routes_scenario,
    routes_summary,
)
from app.core.config import settings
from app.core.exceptions import EconoCausalError
from app.core.logging import get_logger
from app.models.base import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    init_db()
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router)
app.include_router(routes_dataset.router)
app.include_router(routes_run.router)
app.include_router(routes_ite.router)
app.include_router(routes_allocation.router)
app.include_router(routes_refutation.router)
app.include_router(routes_summary.router)
app.include_router(routes_analytics.router)
app.include_router(routes_explainability.router)
app.include_router(routes_recommendation.router)
app.include_router(routes_scenario.router)
app.include_router(routes_drift.router)
app.include_router(routes_history.router)
app.include_router(routes_report.router)
app.include_router(routes_assistant.router)
app.include_router(routes_propensity.router)


@app.exception_handler(EconoCausalError)
def handle_econocausal_error(request: Request, exc: EconoCausalError) -> JSONResponse:
    logger.error("%s: %s", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
    )


@app.get("/health", tags=["health"])
def health_check():
    """Simple liveness check used by the frontend and by manual smoke tests."""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
