"""Rent invoice generation, late fees, and payment reconciliation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease
from app.models.payment import Invoice, InvoiceStatus
from app.utils.dates import BillingPeriod, lease_billing_periods
from app.utils.money import prorate_money


def invoice_amount(lease: Lease, period: BillingPeriod) -> Decimal:
    """Calculate a cent-rounded invoice amount for one billing period."""
    return prorate_money(lease.rent_amount, period.covered_days, period.cycle_days)


def _find_period(lease: Lease, period_start: date | None) -> BillingPeriod:
    periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)
    if period_start is None:
        return periods[0]
    for period in periods:
        if period.period_start == period_start or period.cycle_start == period_start:
            return period
    raise ValueError("period_start does not intersect the lease term")


def build_invoice(lease: Lease, period: BillingPeriod) -> Invoice:
    """Build an unsaved open invoice for ``period``."""
    return Invoice(
        lease_id=lease.id,
        period_start=period.period_start,
        period_end=period.period_end,
        amount_due=invoice_amount(lease, period),
        due_date=period.period_start,
        status=InvoiceStatus.OPEN,
    )


async def generate_invoice(
    db: AsyncSession,
    lease: Lease,
    *,
    period_start: date | None = None,
) -> Invoice:
    """Persist one invoice for a lease billing period.

    The operation is idempotent for the same lease and covered period. When no
    period is supplied, the first period in the lease term is generated.
    """
    period = _find_period(lease, period_start)
    existing = await db.scalar(
        select(Invoice).where(
            Invoice.lease_id == lease.id,
            Invoice.period_start == period.period_start,
            Invoice.period_end == period.period_end,
        )
    )
    if existing is not None:
        return existing

    invoice = build_invoice(lease, period)
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def generate_invoices(db: AsyncSession, lease: Lease) -> list[Invoice]:
    """Persist and return every billing-period invoice for a lease."""
    invoices: list[Invoice] = []
    for period in lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day):
        invoices.append(await generate_invoice(db, lease, period_start=period.period_start))
    return invoices


calculate_invoice_amount = invoice_amount
generate_lease_invoices = generate_invoices


__all__ = [
    "build_invoice",
    "calculate_invoice_amount",
    "generate_invoice",
    "generate_invoices",
    "generate_lease_invoices",
    "invoice_amount",
]
