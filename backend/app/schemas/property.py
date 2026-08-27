"""Pydantic request and response schemas for properties."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.property import PropertyType


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1)
    address_line1: str = Field(min_length=1)
    address_line2: str | None = None
    city: str = Field(min_length=1)
    region: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)
    country: str = Field(min_length=1)
    property_type: PropertyType


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    address_line1: str | None = Field(default=None, min_length=1)
    address_line2: str | None = None
    city: str | None = Field(default=None, min_length=1)
    region: str | None = Field(default=None, min_length=1)
    postal_code: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    property_type: PropertyType | None = None


class PropertyRead(PropertyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PropertyList(BaseModel):
    items: list[PropertyRead]
    total: int
    page: int
    page_size: int


__all__ = ["PropertyCreate", "PropertyList", "PropertyRead", "PropertyUpdate"]
