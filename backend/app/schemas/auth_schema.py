"""Request/response models for /auth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = ""


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserSchema"


class UserSchema(BaseModel):
    user_id: int
    email: str
    full_name: str


TokenSchema.model_rebuild()
