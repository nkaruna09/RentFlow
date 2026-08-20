"""Auth token schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Credentials accepted by the login endpoint."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh token accepted for token rotation."""

    refresh_token: str


class TokenPair(BaseModel):
    """Bearer access and refresh tokens returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


__all__ = ["LoginRequest", "RefreshRequest", "TokenPair"]
