"""Billing-period and proration date helpers.

Lease and invoice periods use half-open intervals: the start date is included
and the end date is excluded. That matches the lease exclusion constraint and
makes adjacent billing periods join without double-counting a day.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BillingPeriod:
    """A lease's covered portion of one complete billing cycle."""

    period_start: date
    period_end: date
    cycle_start: date
    cycle_end: date

    @property
    def covered_days(self) -> int:
        return (self.period_end - self.period_start).days

    @property
    def cycle_days(self) -> int:
        return (self.cycle_end - self.cycle_start).days

    @property
    def is_prorated(self) -> bool:
        return self.period_start != self.cycle_start or self.period_end != self.cycle_end


def _validate_billing_day(billing_day: int) -> None:
    if isinstance(billing_day, bool) or not isinstance(billing_day, int):
        raise TypeError("billing_day must be an integer")
    if not 1 <= billing_day <= 28:
        raise ValueError("billing_day must be between 1 and 28")


def _month_anchor(year: int, month: int, billing_day: int) -> date:
    _validate_billing_day(billing_day)
    return date(year, month, billing_day)


def add_months(value: date, months: int) -> date:
    """Move ``value`` by whole months, clamping to the target month end."""
    if isinstance(months, bool) or not isinstance(months, int):
        raise TypeError("months must be an integer")
    month_index = value.year * 12 + value.month - 1 + months
    year, month_offset = divmod(month_index, 12)
    month = month_offset + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def days_in_month(value: date) -> int:
    """Return the number of calendar days in ``value``'s month."""
    return monthrange(value.year, value.month)[1]


def billing_period_for(value: date, billing_day: int) -> tuple[date, date]:
    """Return the billing cycle containing ``value``.

    ``billing_day`` is constrained to 1-28, matching the documented lease
    range and ensuring every month has an anchor.
    """
    _validate_billing_day(billing_day)
    current_anchor = _month_anchor(value.year, value.month, billing_day)
    if value < current_anchor:
        current_anchor = add_months(current_anchor, -1)
    return current_anchor, add_months(current_anchor, 1)


def lease_billing_periods(
    start_date: date,
    end_date: date,
    billing_day: int,
) -> list[BillingPeriod]:
    """Return all billing periods intersecting a lease term."""
    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")

    cycle_start, cycle_end = billing_period_for(start_date, billing_day)
    periods: list[BillingPeriod] = []
    while cycle_start < end_date:
        period_start = max(start_date, cycle_start)
        period_end = min(end_date, cycle_end)
        if period_start < period_end:
            periods.append(
                BillingPeriod(
                    period_start=period_start,
                    period_end=period_end,
                    cycle_start=cycle_start,
                    cycle_end=cycle_end,
                )
            )
        cycle_start, cycle_end = cycle_end, add_months(cycle_end, 1)
    return periods


get_billing_period = billing_period_for
iter_billing_periods = lease_billing_periods


__all__ = [
    "BillingPeriod",
    "add_months",
    "billing_period_for",
    "days_in_month",
    "get_billing_period",
    "iter_billing_periods",
    "lease_billing_periods",
]
