"""Shared FastAPI dependencies (Volume II Chapter 10.5).

Using Depends(get_db) rather than importing SessionLocal directly in
routes means tests can override this dependency with an in-memory
SQLite session without changing any route or service code.
"""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import NotAuthenticatedError
from app.core.security import decode_access_token
from app.models.base import SessionLocal
from app.models.user import User
from app.repositories import run_repository, user_repository


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)
) -> User:
    """Resolve the caller's User from a `Bearer <token>` header.
    Raises NotAuthenticatedError if the header is missing or invalid.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotAuthenticatedError("Missing or invalid Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        raise NotAuthenticatedError("Invalid or expired token.")
    user_id = payload.get("sub")
    if user_id is None:
        raise NotAuthenticatedError("Invalid token payload.")
    user = user_repository.get(db, int(user_id))
    if user is None:
        raise NotAuthenticatedError("User not found.")
    return user


def verify_run_ownership(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Verify that the authenticated caller owns the run identified by
    ``run_id``. Raises:

    * ``NotAuthenticatedError`` (401) if no valid bearer token is supplied.
    * ``RunNotFoundError`` (404) if the run does not exist **or** the
      caller is authenticated but does not own the run (returns 404
      rather than 403 to avoid leaking the existence of runs owned by
      other users).
    """
    run = run_repository.get(db, run_id)
    if run is None:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(f"No run with id {run_id}.")
    if run.owner_id is not None and run.owner_id != user.user_id:
        from app.core.exceptions import RunNotFoundError
        raise RunNotFoundError(f"No run with id {run_id}.")
