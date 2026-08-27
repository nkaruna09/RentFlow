"""Pydantic response schemas for leases."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.lease import LeaseStatus


class LeaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    start_date: date
    end_date: date
    rent_amount: Decimal
    deposit_amount: Decimal
    billing_day: int
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime


class LeaseList(BaseModel):
    items: list[LeaseRead]
    total: int
    page: int
    page_size: int


__all__ = ["LeaseList", "LeaseRead"]
