"""Entry points for monthly invoicing and overdue-rent scheduled jobs."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.lease import Lease, LeaseStatus
from app.models.payment import Invoice
from app.services import billing_service
from app.utils.dates import add_months, lease_billing_periods

JobName = Literal["monthly-invoicing", "overdue-sweep"]
_BILLABLE_LEASE_STATUSES = (
    LeaseStatus.ACTIVE,
    LeaseStatus.EXPIRED,
    LeaseStatus.TERMINATED,
)


def _utc_today() -> date:
    return datetime.now(UTC).date()


def _month_bounds(value: date) -> tuple[date, date]:
    month_start = value.replace(day=1)
    return month_start, add_months(month_start, 1)


async def run_monthly_invoicing(
    db: AsyncSession,
    *,
    billing_month: date | None = None,
) -> list[Invoice]:
    """Generate invoices for billable lease periods starting in a calendar month.

    ``billing_month`` may be any date in the target month. Invoice generation is
    idempotent for each lease and covered period, so retrying the job is safe.
    """
    month_start, month_end = _month_bounds(billing_month or _utc_today())
    leases = await db.scalars(
        select(Lease)
        .where(
            Lease.status.in_(_BILLABLE_LEASE_STATUSES),
            Lease.start_date < month_end,
            Lease.end_date > month_start,
        )
        .order_by(Lease.id)
    )

    invoices: list[Invoice] = []
    for lease in leases:
        periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)
        for period in periods:
            if month_start <= period.period_start < month_end:
                invoices.append(
                    await billing_service.generate_invoice(
                        db,
                        lease,
                        period_start=period.period_start,
                    )
                )
    return invoices


async def run_overdue_sweep(
    db: AsyncSession,
    *,
    as_of: date | None = None,
) -> list[Invoice]:
    """Apply late fees and mark unpaid invoices overdue as of a UTC date."""
    return await billing_service.apply_late_fees(db, as_of=as_of or _utc_today())


async def run_job(job: JobName, *, run_date: date | None = None) -> list[Invoice]:
    """Run one scheduled job with its own database session."""
    async with async_session_factory() as db:
        if job == "monthly-invoicing":
            return await run_monthly_invoicing(db, billing_month=run_date)
        if job == "overdue-sweep":
            return await run_overdue_sweep(db, as_of=run_date)
        raise ValueError(f"unknown scheduled job: {job}")


def main() -> None:
    """Run a job from an Azure Container Apps job command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=("monthly-invoicing", "overdue-sweep"))
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Override the UTC run date (YYYY-MM-DD), primarily for recovery runs.",
    )
    arguments = parser.parse_args()
    asyncio.run(run_job(arguments.job, run_date=arguments.date))


if __name__ == "__main__":
    main()


__all__ = ["JobName", "run_job", "run_monthly_invoicing", "run_overdue_sweep"]
