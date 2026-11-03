"""
SQLAlchemy declarative base and engine/session setup.

Table creation is handled by Base.metadata.create_all() on application
startup (Volume II Chapter 8.6) -- sufficient for this internship's
single-environment, SQLite-backed scope. Adopting Alembic migrations is
an OPTIONAL enhancement (Volume II Chapter 17).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    # Import models so they are registered on Base.metadata before create_all().
    from app.models import (  # noqa: F401
        dataset,
        customer,
        run,
        ite_score,
        allocation,
        refutation_result,
        user,
        drift_result,
        feature_importance,
        propensity_score,
        propensity_diagnostic,
        balance_metric,
        recommendation_result,
        password_reset_token,
    )

    Base.metadata.create_all(bind=engine)
