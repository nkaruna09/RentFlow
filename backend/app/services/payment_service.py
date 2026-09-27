"""Invoice creation, payment reconciliation, and arrears business rules."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.payment import Invoice, InvoiceStatus, Payment
from app.models.user import User
from app.repositories import lease as lease_repository
from app.repositories import payment as payment_repository
from app.schemas.payment import ArrearsItem


async def list_invoices(
    db: AsyncSession,
    current_user: User,
    *,
    lease_id: uuid.UUID | None,
    status: InvoiceStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Invoice], int]:
    return await payment_repository.list_for_owner(
        db,
        current_user.id,
        lease_id=lease_id,
        invoice_status=status,
        page=page,
        page_size=page_size,
    )


async def create_invoice(
    db: AsyncSession,
    current_user: User,
    values: dict[str, object],
) -> Invoice:
    lease_id = values.get("lease_id")
    if not isinstance(lease_id, uuid.UUID):
        raise ValidationError("Invoice lease_id is invalid")
    lease = await lease_repository.get_visible(db, lease_id, current_user.id, current_user.role)
    if lease is None:
        raise NotFoundError("Lease not found")

    period_start = values.get("period_start")
    period_end = values.get("period_end")
    due_date = values.get("due_date")
    if (
        not isinstance(period_start, date)
        or not isinstance(period_end, date)
        or not isinstance(due_date, date)
    ):
        raise ValidationError("Invoice dates are invalid")
    if period_end <= period_start:
        raise ValidationError("Invoice period_end must be after period_start")

    values["status"] = InvoiceStatus.OPEN
    try:
        return await payment_repository.create_invoice(db, values)
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("An invoice already exists for this lease period") from exc


async def get_invoice(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    current_user: User,
) -> Invoice:
    invoice = await payment_repository.get_for_owner(db, invoice_id, current_user.id)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    return invoice


async def record_payment(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    current_user: User,
    values: dict[str, object],
) -> Payment:
    invoice = await payment_repository.get_for_owner(
        db, invoice_id, current_user.id, for_update=True
    )
    if invoice is None:
        raise NotFoundError("Invoice not found")
    if invoice.status == InvoiceStatus.VOID:
        raise ConflictError("Cannot record a payment against a void invoice")

    amount = values.get("amount")
    if not isinstance(amount, Decimal) or amount <= 0:
        raise ValidationError("Payment amount must be positive")
    amount_paid = await payment_repository.total_paid(db, invoice.id)
    new_total = amount_paid + amount
    if new_total > invoice.amount_due:
        raise ValidationError("Payment exceeds the invoice's outstanding balance")

    invoice.status = (
        InvoiceStatus.PAID if new_total == invoice.amount_due else InvoiceStatus.PARTIAL
    )
    payment = Payment(invoice_id=invoice.id, **values)
    return await payment_repository.create_payment(db, payment, invoice)


async def list_arrears(
    db: AsyncSession,
    current_user: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[ArrearsItem], int, Decimal]:
    rows, total, outstanding_total = await payment_repository.list_arrears(
        db, current_user.id, page=page, page_size=page_size
    )
    return (
        [ArrearsItem(lease_id=lease_id, outstanding_balance=balance) for lease_id, balance in rows],
        total,
        outstanding_total,
    )


__all__ = ["create_invoice", "get_invoice", "list_arrears", "list_invoices", "record_payment"]
