"""Invoice and payment endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.payment import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.payment import (
    ArrearsList,
    InvoiceCreate,
    InvoiceList,
    InvoiceRead,
    PaymentCreate,
    PaymentRead,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])
payment_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentPaymentManager = Annotated[User, Depends(payment_managers)]


@router.get("/invoices", response_model=InvoiceList)
async def list_invoices(
    current_user: CurrentPaymentManager,
    db: AsyncSession = Depends(get_db),
    lease_id: uuid.UUID | None = None,
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> InvoiceList:
    invoices, total = await payment_service.list_invoices(
        db,
        current_user,
        lease_id=lease_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return InvoiceList(
        items=[InvoiceRead.model_validate(invoice) for invoice in invoices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    current_user: CurrentPaymentManager,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    invoice = await payment_service.create_invoice(db, current_user, invoice_in.model_dump())
    return InvoiceRead.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentPaymentManager,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    invoice = await payment_service.get_invoice(db, invoice_id, current_user)
    return InvoiceRead.model_validate(invoice)


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    invoice_id: uuid.UUID,
    payment_in: PaymentCreate,
    current_user: CurrentPaymentManager,
    db: AsyncSession = Depends(get_db),
) -> PaymentRead:
    payment = await payment_service.record_payment(
        db, invoice_id, current_user, payment_in.model_dump()
    )
    return PaymentRead.model_validate(payment)


@router.get("/arrears", response_model=ArrearsList)
async def list_arrears(
    current_user: CurrentPaymentManager,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> ArrearsList:
    items, total, outstanding_total = await payment_service.list_arrears(
        db, current_user, page=page, page_size=page_size
    )
    return ArrearsList(
        items=items,
        total=total,
        outstanding_total=outstanding_total,
        page=page,
        page_size=page_size,
    )
