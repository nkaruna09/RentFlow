"""Pydantic request and response schemas for tenants."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    user_id: uuid.UUID | None = None
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    emergency_contact: dict[str, Any] | None = None


class TenantUpdate(BaseModel):
    user_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1)
    emergency_contact: dict[str, Any] | None = None


class TenantRead(TenantCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TenantList(BaseModel):
    items: list[TenantRead]
    total: int
    page: int
    page_size: int


__all__ = ["TenantCreate", "TenantList", "TenantRead", "TenantUpdate"]
