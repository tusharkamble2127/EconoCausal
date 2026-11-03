"""Business logic for password reset flow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import InvalidResetTokenError, RateLimitError
from app.core.security import generate_reset_token, hash_password
from app.models.password_reset_token import PasswordResetToken
from app.repositories import user_repository
from app.schemas.password_reset_schema import ResetPasswordSchema
from app.services.email_service import EmailError, send_password_reset_email

RESET_COOLDOWN_SECONDS = 60


def forgot_password(db: Session, email: str) -> dict:
    user = user_repository.get_by_email(db, email)
    if user is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=RESET_COOLDOWN_SECONDS)
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.user_id)
            .where(PasswordResetToken.used_at.is_(None))
            .where(PasswordResetToken.expires_at > datetime.now(timezone.utc))
            .where(PasswordResetToken.created_at > cutoff)
            .order_by(PasswordResetToken.created_at.desc())
        )
        recent = db.execute(stmt).scalars().first()
        if recent is not None:
            raise RateLimitError("Please wait before requesting another reset.")

        raw_token = generate_reset_token()
        from app.repositories.password_reset_repository import create as create_token
        create_token(db, user, raw_token, settings.password_reset_expire_minutes)

        reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={raw_token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except EmailError:
            pass

    return {"message": "If an account exists for this email, a password reset link has been sent."}


def reset_password(db: Session, payload: ResetPasswordSchema) -> dict:
    from app.repositories.password_reset_repository import get_valid_token, mark_used
    record = get_valid_token(db, payload.token)
    if record is None:
        raise InvalidResetTokenError("This password reset link is invalid or has expired.")

    user = user_repository.get(db, record.user_id)
    if user is None:
        raise InvalidResetTokenError("This password reset link is invalid or has expired.")

    user.hashed_password = hash_password(payload.new_password)
    mark_used(db, record)
    db.commit()

    return {"message": "Your password has been reset successfully."}
