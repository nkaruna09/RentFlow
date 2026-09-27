"""Owner-scoped invoice, payment, and arrears persistence queries."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.lease import Lease
from app.models.payment import Invoice, InvoiceStatus, Payment
from app.models.property import Property
from app.models.unit import Unit
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice


class PaymentRepository(BaseRepository[Payment]):
    model = Payment


invoice_repository = InvoiceRepository()
payment_repository = PaymentRepository()


def _owner_invoices(owner_id: uuid.UUID) -> Select[tuple[Invoice]]:
    return (
        select(Invoice)
        .join(Lease, Invoice.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == owner_id)
    )


async def list_for_owner(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    lease_id: uuid.UUID | None,
    invoice_status: InvoiceStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Invoice], int]:
    scope = _owner_invoices(owner_id)
    if lease_id is not None:
        scope = scope.where(Invoice.lease_id == lease_id)
    if invoice_status is not None:
        scope = scope.where(Invoice.status == invoice_status)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Invoice.due_date.desc(), Invoice.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.all()), total


async def get_for_owner(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Invoice | None:
    query = _owner_invoices(owner_id).where(Invoice.id == invoice_id)
    if for_update:
        query = query.with_for_update(of=Invoice)
    return cast(Invoice | None, await db.scalar(query))


async def create_invoice(db: AsyncSession, values: dict[str, object]) -> Invoice:
    return await invoice_repository.create(db, values)


async def total_paid(db: AsyncSession, invoice_id: uuid.UUID) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
            Payment.invoice_id == invoice_id
        )
    )
    return Decimal(total or 0)


async def create_payment(db: AsyncSession, payment: Payment, invoice: Invoice) -> Payment:
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    await db.refresh(invoice)
    return payment


async def list_arrears(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> tuple[list[tuple[uuid.UUID, Decimal]], int, Decimal]:
    payment_totals = (
        select(Payment.invoice_id, func.sum(Payment.amount).label("amount_paid"))
        .group_by(Payment.invoice_id)
        .subquery()
    )
    balance = Invoice.amount_due - func.coalesce(payment_totals.c.amount_paid, Decimal("0.00"))
    arrears = (
        select(
            Lease.id.label("lease_id"),
            func.sum(balance).label("outstanding_balance"),
        )
        .join(Invoice, Invoice.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .outerjoin(payment_totals, payment_totals.c.invoice_id == Invoice.id)
        .where(
            Property.owner_id == owner_id,
            Invoice.status.not_in((InvoiceStatus.PAID, InvoiceStatus.VOID)),
            balance > 0,
        )
        .group_by(Lease.id)
    )
    summary = arrears.subquery()
    total = int(await db.scalar(select(func.count()).select_from(summary)) or 0)
    outstanding_total = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(summary.c.outstanding_balance), Decimal("0.00")))
        )
        or 0
    )
    rows = await db.execute(
        arrears.order_by(Lease.id).offset((page - 1) * page_size).limit(page_size)
    )
    items = [(row.lease_id, Decimal(row.outstanding_balance)) for row in rows]
    return items, total, outstanding_total


__all__ = [
    "create_invoice",
    "create_payment",
    "get_for_owner",
    "list_arrears",
    "list_for_owner",
    "total_paid",
]
