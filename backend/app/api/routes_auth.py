"""POST /auth/register, POST /auth/login, POST /auth/forgot-password, POST /auth/reset-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth_schema import LoginSchema, RegisterSchema, TokenSchema
from app.schemas.password_reset_schema import ForgotPasswordSchema, ResetPasswordSchema, ResetPasswordResponseSchema
from app.services import auth_service, password_reset_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenSchema, status_code=201)
def register(payload: RegisterSchema, db: Session = Depends(get_db)):
    """Create a new user account and return a bearer token."""
    return auth_service.register(db, payload)


@router.post("/login", response_model=TokenSchema)
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    """Authenticate and return a bearer token."""
    return auth_service.login(db, payload)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordSchema, db: Session = Depends(get_db)):
    """Initiate a password reset flow. Always returns a generic message."""
    return password_reset_service.forgot_password(db, payload.email)


@router.post("/reset-password", response_model=ResetPasswordResponseSchema)
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    """Complete a password reset using a valid token."""
    return password_reset_service.reset_password(db, payload)
