"""
Custom exception hierarchy.

Volume II Chapter 6.8: services raise these; a single FastAPI exception
handler (registered in app/main.py) converts each one to the standard
error envelope (Volume II Chapter 7.7) with the correct HTTP status code.
Never let a raw stack trace reach the API response.
"""
from __future__ import annotations


class EconoCausalError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = 400


class DatasetNotFoundError(EconoCausalError):
    status_code = 404


class RunNotFoundError(EconoCausalError):
    status_code = 404


class InvalidDatasetError(EconoCausalError):
    status_code = 422


class InsufficientTreatmentVariationError(EconoCausalError):
    """Raised when a dataset's treatment column has fewer than the
    minimum required number of distinct values (Volume I Chapter 7.5)."""

    status_code = 422


class RunNotCompleteError(EconoCausalError):
    """Raised when ITE/allocation/refutation results are requested for
    a run that has not finished training (Volume II Chapter 7.4-7.6)."""

    status_code = 409


class InvalidCredentialsError(EconoCausalError):
    status_code = 401


class UserAlreadyExistsError(EconoCausalError):
    status_code = 409


class NotAuthenticatedError(EconoCausalError):
    status_code = 401


class CampaignNotFoundError(EconoCausalError):
    status_code = 404


class InvalidResetTokenError(EconoCausalError):
    status_code = 400


class ExpiredResetTokenError(EconoCausalError):
    status_code = 400


class RateLimitError(EconoCausalError):
    status_code = 429
