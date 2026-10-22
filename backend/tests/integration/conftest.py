"""Shared fixtures for integration tests (Volume II Chapter 10.5, Chapter 12 Day 23).

Overrides the get_db dependency with an in-memory SQLite session so
integration tests never touch the real econocausal.db file.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.main import app
from app.models.base import Base

_test_engine = None
_TestingSessionLocal = None


@pytest.fixture()
def client():
    global _test_engine, _TestingSessionLocal
    _test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
    Base.metadata.create_all(bind=_test_engine)

    def override_get_db():
        db = _TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    _test_engine = None
    _TestingSessionLocal = None


@pytest.fixture()
def sample_dataset_payload():
    rows = []
    for i in range(60):
        loyalty = (i % 10) / 10.0
        treatment = [0.0, 10.0, 20.0][i % 3]
        outcome = 1 if (loyalty + treatment / 100.0) > 0.5 else 0
        rows.append(
            {
                "features": {"loyalty_score": loyalty, "tenure_months": float(i)},
                "treatment": treatment,
                "outcome": outcome,
            }
        )
    return {"name": "integration_test_dataset", "rows": rows}


@pytest.fixture()
def owner_user(client):
    """Register an owner user via the API and return (user_id, token)."""
    resp = client.post(
        "/auth/register",
        json={"email": "owner@test.com", "password": "pass123", "full_name": "Owner"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["user"]["user_id"], data["access_token"]


@pytest.fixture()
def other_user(client):
    """Register a second user via the API and return (user_id, token)."""
    resp = client.post(
        "/auth/register",
        json={"email": "attacker@test.com", "password": "pass123", "full_name": "Attacker"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["user"]["user_id"], data["access_token"]


@pytest.fixture()
def owner_headers(owner_user):
    return {"Authorization": f"Bearer {owner_user[1]}"}


@pytest.fixture()
def other_headers(other_user):
    return {"Authorization": f"Bearer {other_user[1]}"}


@pytest.fixture()
def db_session(client):
    from app.api.deps import get_db

    original_override = app.dependency_overrides.get(get_db)
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        if original_override is not None:
            app.dependency_overrides[get_db] = original_override
        else:
            app.dependency_overrides.pop(get_db, None)

