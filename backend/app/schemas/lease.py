"""Pydantic request and response schemas for leases."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.lease import LeaseStatus


class LeaseCreate(BaseModel):
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    start_date: date
    end_date: date
    rent_amount: Decimal
    deposit_amount: Decimal
    billing_day: int
    status: LeaseStatus = LeaseStatus.DRAFT


class LeaseUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = None
    deposit_amount: Decimal | None = None
    billing_day: int | None = None


class LeaseRenewRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = None
    deposit_amount: Decimal | None = None
    billing_day: int | None = None


class LeaseTerminateRequest(BaseModel):
    reason: str = Field(min_length=1)
    end_date: date


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


__all__ = [
    "LeaseCreate",
    "LeaseList",
    "LeaseRead",
    "LeaseRenewRequest",
    "LeaseTerminateRequest",
    "LeaseUpdate",
]
