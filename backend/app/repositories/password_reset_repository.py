"""Data access for password reset tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_reset_token
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def create(db: Session, user: User, raw_token: str, expires_minutes: int) -> PasswordResetToken:
    now = datetime.now(timezone.utc)
    record = PasswordResetToken(
        user_id=user.user_id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now + timedelta(minutes=expires_minutes),
        used_at=None,
        created_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_valid_token(db: Session, raw_token: str) -> Optional[PasswordResetToken]:
    token_hash = hash_reset_token(raw_token)
    stmt = (
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .where(PasswordResetToken.used_at.is_(None))
        .where(PasswordResetToken.expires_at > datetime.now(timezone.utc))
    )
    return db.execute(stmt).scalars().first()


def mark_used(db: Session, record: PasswordResetToken) -> None:
    record.used_at = datetime.now(timezone.utc)
    db.commit()
