"""Request/response models for password reset endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class ResetPasswordResponseSchema(BaseModel):
    message: str
