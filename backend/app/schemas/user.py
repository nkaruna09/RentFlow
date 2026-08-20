"""Pydantic request/response schemas for users."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Fields accepted when registering a user."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    role: UserRole


class UserUpdate(BaseModel):
    """Fields accepted when updating a user."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    full_name: str | None = Field(default=None, min_length=1)
    role: UserRole | None = None
    is_active: bool | None = None


class UserPublic(BaseModel):
    """Safe user fields suitable for embedding in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class UserRead(UserPublic):
    """Complete safe user response, including audit timestamps."""

    created_at: datetime
    updated_at: datetime


__all__ = ["UserCreate", "UserPublic", "UserRead", "UserUpdate"]
