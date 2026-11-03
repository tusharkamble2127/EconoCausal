"""Unit tests for JWT configuration security validation."""
from __future__ import annotations

import os

import pytest

from app.core.config import Settings


def test_valid_configured_secret_allowed_in_development():
    os.environ["ECONOCAUSAL_ENV"] = "development"
    os.environ["ECONOCAUSAL_JWT_SECRET"] = "a-valid-secret-for-dev"
    try:
        settings = Settings()
        assert settings.jwt_secret_key == "a-valid-secret-for-dev"
        assert settings.app_env == "development"
    finally:
        os.environ.pop("ECONOCAUSAL_ENV", None)
        os.environ.pop("ECONOCAUSAL_JWT_SECRET", None)


def test_insecure_default_secret_rejected_in_production():
    os.environ["ECONOCAUSAL_ENV"] = "production"
    os.environ["ECONOCAUSAL_JWT_SECRET"] = "dev-only-insecure-secret-change-me"
    with pytest.raises(ValueError, match="ECONOCAUSAL_JWT_SECRET must be set"):
        Settings()
    os.environ.pop("ECONOCAUSAL_ENV", None)
    os.environ.pop("ECONOCAUSAL_JWT_SECRET", None)


def test_missing_secret_rejected_in_production():
    os.environ["ECONOCAUSAL_ENV"] = "production"
    os.environ.pop("ECONOCAUSAL_JWT_SECRET", None)
    with pytest.raises(ValueError, match="ECONOCAUSAL_JWT_SECRET must be set"):
        Settings()
    os.environ.pop("ECONOCAUSAL_ENV", None)


def test_development_mode_allows_insecure_default():
    os.environ["ECONOCAUSAL_ENV"] = "development"
    os.environ.pop("ECONOCAUSAL_JWT_SECRET", None)
    try:
        settings = Settings()
        assert settings.jwt_secret_key == "dev-only-insecure-secret-change-me"
    finally:
        os.environ.pop("ECONOCAUSAL_ENV", None)


def test_development_mode_allows_valid_secret():
    os.environ["ECONOCAUSAL_ENV"] = "development"
    os.environ["ECONOCAUSAL_JWT_SECRET"] = "another-valid-secret"
    try:
        settings = Settings()
        assert settings.jwt_secret_key == "another-valid-secret"
    finally:
        os.environ.pop("ECONOCAUSAL_ENV", None)
        os.environ.pop("ECONOCAUSAL_JWT_SECRET", None)
