"""Pydantic response schemas for units."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.unit import UnitStatus


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    label: str
    bedrooms: Decimal
    bathrooms: Decimal
    square_feet: int | None
    market_rent: Decimal
    status: UnitStatus
    created_at: datetime
    updated_at: datetime


class UnitList(BaseModel):
    items: list[UnitRead]
    total: int
    page: int
    page_size: int


__all__ = ["UnitList", "UnitRead"]
