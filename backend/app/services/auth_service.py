"""Business logic for registration/login (Phase 3 -- authentication)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user_repository
from app.schemas.auth_schema import LoginSchema, RegisterSchema, TokenSchema, UserSchema


def register(db: Session, payload: RegisterSchema) -> TokenSchema:
    existing = user_repository.get_by_email(db, payload.email)
    if existing is not None:
        raise UserAlreadyExistsError(f"An account with email {payload.email} already exists.")

    user = user_repository.create(db, payload.email, hash_password(payload.password), payload.full_name)
    token = create_access_token(subject=str(user.user_id))
    return TokenSchema(
        access_token=token,
        user=UserSchema(user_id=user.user_id, email=user.email, full_name=user.full_name),
    )


def login(db: Session, payload: LoginSchema) -> TokenSchema:
    user = user_repository.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect email or password.")

    token = create_access_token(subject=str(user.user_id))
    return TokenSchema(
        access_token=token,
        user=UserSchema(user_id=user.user_id, email=user.email, full_name=user.full_name),
    )
