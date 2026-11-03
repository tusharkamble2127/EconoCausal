"""Integration tests for password reset flow."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.security import hash_reset_token, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.repositories import password_reset_repository, user_repository
from app.core.security import generate_reset_token


def test_forgot_password_returns_generic_message_for_nonexistent_email(client):
    resp = client.post("/auth/forgot-password", json={"email": "no-such@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "If an account exists for this email, a password reset link has been sent."


def test_forgot_password_returns_generic_message_for_existing_user(client, owner_user):
    resp = client.post("/auth/forgot-password", json={"email": "owner@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "If an account exists for this email, a password reset link has been sent."


def test_forgot_password_validates_email_format(client):
    resp = client.post("/auth/forgot-password", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_forgot_password_rate_limit(client, owner_user, db_session):
    resp1 = client.post("/auth/forgot-password", json={"email": "owner@test.com"})
    assert resp1.status_code == 200
    resp2 = client.post("/auth/forgot-password", json={"email": "owner@test.com"})
    assert resp2.status_code == 429


def test_reset_password_success_flow(client, owner_user, db_session):
    owner_email = "owner@test.com"
    raw_token = generate_reset_token()
    user = user_repository.get(db_session, owner_user[0])
    password_reset_repository.create(db_session, user, raw_token, 30)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "newpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Your password has been reset successfully."

    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_reset_token(raw_token))
    token_row = db_session.execute(stmt).scalars().first()
    db_session.refresh(token_row)
    assert token_row.used_at is not None

    db_session.refresh(user)
    assert verify_password("newpass123", user.hashed_password)
    assert not verify_password("pass123", user.hashed_password)

    resp = client.post("/auth/login", json={"email": owner_email, "password": "newpass123"})
    assert resp.status_code == 200

    resp = client.post("/auth/login", json={"email": owner_email, "password": "pass123"})
    assert resp.status_code == 401


def test_reset_password_invalid_token(client):
    resp = client.post("/auth/reset-password", json={"token": "invalid-token", "new_password": "newpass123"})
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


def test_reset_password_weak_password(client, owner_user):
    resp = client.post("/auth/reset-password", json={"token": "invalid", "new_password": "123"})
    assert resp.status_code == 422


def test_reset_password_token_is_one_time_use(client, owner_user, db_session):
    owner_email = "owner@test.com"
    raw_token = generate_reset_token()
    user = user_repository.get(db_session, owner_user[0])
    password_reset_repository.create(db_session, user, raw_token, 30)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "newpass123"})
    assert resp.status_code == 200

    resp = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "anotherpass123"})
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


def test_reset_password_mismatch(client):
    resp = client.post("/auth/reset-password", json={"token": "x", "new_password": "abc"})
    assert resp.status_code == 422
