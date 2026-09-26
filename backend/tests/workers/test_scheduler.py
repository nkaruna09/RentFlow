"""Scheduled billing job tests."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease, LeaseStatus
from app.models.payment import Invoice, InvoiceStatus
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.workers.scheduler import run_monthly_invoicing, run_overdue_sweep


async def _persist_lease(db: AsyncSession, make_user) -> Lease:
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Scheduler property",
        address_line1="3 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M3",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 3",
        bedrooms=1,
        bathrooms=1,
        market_rent=Decimal("1000.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        full_name="Scheduled Tenant",
        email="scheduled-tenant@example.com",
        phone="555-0102",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 1),
        rent_amount=Decimal("1000.00"),
        deposit_amount=Decimal("1000.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db.add_all([property_, unit, tenant, lease])
    await db.flush()
    return lease


async def test_monthly_invoicing_is_idempotent(db_session: AsyncSession, make_user) -> None:
    lease = await _persist_lease(db_session, make_user)

    first_run = await run_monthly_invoicing(db_session, billing_month=date(2026, 2, 1))
    second_run = await run_monthly_invoicing(db_session, billing_month=date(2026, 2, 20))
    invoice_count = await db_session.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.lease_id == lease.id)
    )

    assert len(first_run) == 1
    assert [invoice.id for invoice in second_run] == [first_run[0].id]
    assert invoice_count == 1
    assert first_run[0].period_start == date(2026, 2, 1)


async def test_overdue_sweep_marks_invoice_and_charges_once(
    db_session: AsyncSession, make_user
) -> None:
    await _persist_lease(db_session, make_user)
    invoices = await run_monthly_invoicing(db_session, billing_month=date(2026, 1, 1))

    first_run = await run_overdue_sweep(db_session, as_of=date(2026, 1, 2))
    second_run = await run_overdue_sweep(db_session, as_of=date(2026, 1, 2))
    await db_session.refresh(invoices[0])

    assert [invoice.id for invoice in first_run] == [invoices[0].id]
    assert second_run == []
    assert invoices[0].amount_due == Decimal("1020.00")
    assert invoices[0].status is InvoiceStatus.OVERDUE
