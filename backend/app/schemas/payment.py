"""Pydantic schemas for invoices and payments."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import InvoiceStatus, PaymentMethod


class InvoiceCreate(BaseModel):
    """Fields accepted when creating an invoice."""

    lease_id: uuid.UUID
    period_start: date
    period_end: date
    amount_due: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.OPEN


class InvoiceUpdate(BaseModel):
    """Fields that may be changed on an invoice."""

    period_start: date | None = None
    period_end: date | None = None
    amount_due: Decimal | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None


class InvoiceRead(InvoiceCreate):
    """Invoice fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    late_fee_amount: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceList(BaseModel):
    items: list[InvoiceRead]
    total: int
    page: int
    page_size: int


class PaymentCreate(BaseModel):
    """Fields accepted when recording a payment."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    paid_at: datetime
    method: PaymentMethod
    reference: str | None = None


class PaymentRead(PaymentCreate):
    """Payment fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ArrearsItem(BaseModel):
    """Outstanding balance aggregated for one lease."""

    lease_id: uuid.UUID
    outstanding_balance: Decimal


class ArrearsList(BaseModel):
    """Owner-scoped arrears totals, paginated by lease."""

    items: list[ArrearsItem]
    total: int
    outstanding_total: Decimal
    page: int
    page_size: int


class PaymentList(BaseModel):
    items: list[PaymentRead]
    total: int
    page: int
    page_size: int


__all__ = [
    "ArrearsItem",
    "ArrearsList",
    "InvoiceCreate",
    "InvoiceList",
    "InvoiceRead",
    "InvoiceStatus",
    "InvoiceUpdate",
    "PaymentCreate",
    "PaymentList",
    "PaymentMethod",
    "PaymentRead",
]
