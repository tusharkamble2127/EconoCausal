"""
Application-wide configuration.

Centralizing configuration here means every other module (database session,
CORS origins, default optimizer settings) reads from one place instead of
scattering magic values across the codebase.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Settings:
    app_name: str = "EconoCausal API"
    app_version: str = "1.0.0"

    # SQLite database file, relative to the backend/ working directory.
    database_url: str = os.environ.get("ECONOCAUSAL_DB_URL", "sqlite:///./econocausal.db")

    # Origins allowed to call this API from the browser (the Vite dev server).
    cors_origins: List[str] = field(
        default_factory=lambda: os.environ.get(
            "ECONOCAUSAL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
    )

    # Default causal-ML pipeline settings (Volume I Chapter 8, Volume II Chapter 11).
    default_base_estimator: str = "RandomForest"
    candidate_discount_levels: tuple = (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0)
    min_treatment_variation: int = 2  # minimum distinct treatment values required

    # Optimizer settings (Volume II Chapter 8 / Chapter 12 Day 15-17).
    optimizer_method: str = "highs"  # scipy.optimize.linprog method

    # Data drift detector settings (Volume II Chapter 11.9).
    drift_p_value_threshold: float = 0.05

    # Revenue assumption used to translate ITE (a probability-of-purchase
    # delta) into a dollar incremental-revenue estimate for the KPI cards
    # and reports. This is a simplifying business assumption, not a fitted
    # value -- documented here so it's easy to find and override.
    assumed_revenue_per_conversion: float = float(os.environ.get("ECONOCAUSAL_REVENUE_PER_CONVERSION", "100.0"))

    # Auth settings. ECONOCAUSAL_JWT_SECRET should always be overridden via
    # environment variable in any non-local deployment.
    app_env: str = field(default="development")
    jwt_secret_key: str = field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.environ.get("ECONOCAUSAL_JWT_EXPIRE_MINUTES", "480"))

    # Email / password reset settings.
    smtp_host: str = os.environ.get("ECONOCAUSAL_SMTP_HOST", "")
    smtp_port: int = int(os.environ.get("ECONOCAUSAL_SMTP_PORT", "587"))
    smtp_username: str = os.environ.get("ECONOCAUSAL_SMTP_USERNAME", "")
    smtp_password: str = os.environ.get("ECONOCAUSAL_SMTP_PASSWORD", "")
    smtp_from_email: str = os.environ.get("ECONOCAUSAL_SMTP_FROM_EMAIL", "")
    smtp_use_tls: bool = os.environ.get("ECONOCAUSAL_SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    password_reset_expire_minutes: int = int(os.environ.get("ECONOCAUSAL_PASSWORD_RESET_EXPIRE_MINUTES", "30"))
    frontend_base_url: str = os.environ.get("ECONOCAUSAL_FRONTEND_BASE_URL", "http://localhost:5173")

    # Brevo transactional email settings.
    brevo_api_key: str = os.environ.get("ECONOCAUSAL_BREVO_API_KEY", "")
    brevo_template_id: str = os.environ.get("ECONOCAUSAL_BREVO_TEMPLATE_ID", "")

    def __post_init__(self):
        env = os.environ.get("ECONOCAUSAL_ENV", "development")
        secret = os.environ.get("ECONOCAUSAL_JWT_SECRET", "dev-only-insecure-secret-change-me")
        object.__setattr__(self, "app_env", env)
        object.__setattr__(self, "jwt_secret_key", secret)

        if env != "development":
            if not os.environ.get("ECONOCAUSAL_JWT_SECRET") or secret == "dev-only-insecure-secret-change-me":
                raise ValueError(
                    "ECONOCAUSAL_JWT_SECRET must be set to a secure, non-default value when ECONOCAUSAL_ENV is not 'development'."
                )


settings = Settings()
