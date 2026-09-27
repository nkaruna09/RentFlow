"""Money and billing boundary-condition tests."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease, LeaseStatus
from app.models.payment import InvoiceStatus
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.services.billing_service import (
    LATE_FEE_AMOUNT,
    apply_late_fees,
    build_invoice,
    generate_invoice,
)
from app.utils.dates import lease_billing_periods
from app.utils.money import format_money, prorate_money, round_money, split_money


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.004", Decimal("10.00")),
        ("10.005", Decimal("10.01")),
        ("-10.005", Decimal("-10.01")),
    ],
)
def test_round_money_uses_half_up_for_fractional_cents(value: str, expected: Decimal) -> None:
    assert round_money(value) == expected


def test_prorate_money_rounds_fractional_cent_after_decimal_arithmetic() -> None:
    # 10.00 * 1 / 6 = 1.666..., which must become 1.67 rather than 1.66.
    assert prorate_money(Decimal("10.00"), 1, 6) == Decimal("1.67")


def test_split_money_preserves_rounded_total_and_distributes_remainder() -> None:
    result = split_money(Decimal("10.00"), 3)

    assert result == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]
    assert sum(result, Decimal("0")) == Decimal("10.00")


def test_split_money_handles_negative_remainder() -> None:
    result = split_money(Decimal("-10.01"), 3)

    assert result == [Decimal("-3.33"), Decimal("-3.34"), Decimal("-3.34")]
    assert sum(result, Decimal("0")) == Decimal("-10.01")


def test_format_money_is_deterministic_and_cent_precise() -> None:
    assert format_money("1234.565") == "$1,234.57"
    assert format_money(Decimal("-12"), currency="€") == "-€12.00"


def test_money_helpers_reject_float_inputs() -> None:
    with pytest.raises(TypeError):
        round_money(10.005)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_money_helpers_reject_non_finite_values(value: str) -> None:
    with pytest.raises(ValueError, match="finite"):
        round_money(value)


@pytest.mark.parametrize(
    ("numerator", "denominator", "message"),
    [
        (-1, 30, "numerator must be non-negative"),
        (1, 0, "denominator must be positive"),
        (1, -30, "denominator must be positive"),
    ],
)
def test_proration_rejects_invalid_ratios(numerator: int, denominator: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        prorate_money("100.00", numerator, denominator)


@pytest.mark.parametrize("parts", [0, -1, True, 1.5])
def test_split_money_requires_a_positive_integer(parts: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        split_money("10.00", parts)  # type: ignore[arg-type]


def _lease(*, start: date, end: date, status: LeaseStatus = LeaseStatus.ACTIVE) -> Lease:
    return Lease(
        id=uuid4(),
        unit_id=uuid4(),
        tenant_id=uuid4(),
        start_date=start,
        end_date=end,
        rent_amount=Decimal("1000.00"),
        deposit_amount=Decimal("1000.00"),
        billing_day=1,
        status=status,
    )


def test_lease_starting_on_the_first_gets_full_monthly_periods() -> None:
    lease = _lease(start=date(2026, 1, 1), end=date(2026, 4, 1))

    periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)

    assert [(period.period_start, period.period_end) for period in periods] == [
        (date(2026, 1, 1), date(2026, 2, 1)),
        (date(2026, 2, 1), date(2026, 3, 1)),
        (date(2026, 3, 1), date(2026, 4, 1)),
    ]
    assert [build_invoice(lease, period).amount_due for period in periods] == [
        Decimal("1000.00"),
        Decimal("1000.00"),
        Decimal("1000.00"),
    ]


def test_mid_month_lease_start_prorates_first_invoice() -> None:
    lease = _lease(start=date(2026, 1, 15), end=date(2026, 3, 1))

    periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)

    first = build_invoice(lease, periods[0])
    assert (first.period_start, first.period_end) == (date(2026, 1, 15), date(2026, 2, 1))
    assert first.amount_due == Decimal("548.39")  # 17 of January's 31 days


def test_lease_starting_on_last_day_prorates_one_day() -> None:
    lease = _lease(start=date(2026, 1, 31), end=date(2026, 3, 1))

    periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)

    first = build_invoice(lease, periods[0])
    assert (first.period_start, first.period_end) == (date(2026, 1, 31), date(2026, 2, 1))
    assert first.amount_due == Decimal("32.26")


def test_terminated_mid_period_prorates_last_invoice() -> None:
    lease = _lease(
        start=date(2026, 1, 1),
        end=date(2026, 1, 15),
        status=LeaseStatus.TERMINATED,
    )

    periods = lease_billing_periods(lease.start_date, lease.end_date, lease.billing_day)

    invoice = build_invoice(lease, periods[0])
    assert (invoice.period_start, invoice.period_end) == (date(2026, 1, 1), date(2026, 1, 15))
    assert invoice.amount_due == Decimal("451.61")  # 14 of January's 31 days


async def test_generate_invoice_persists_and_is_idempotent(
    db_session: AsyncSession, make_user
) -> None:
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Billing property",
        address_line1="1 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M1",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 1",
        bedrooms=1,
        bathrooms=1,
        market_rent=Decimal("1000.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        full_name="Billing Tenant",
        email="billing-service@example.com",
        phone="555-0100",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 15),
        end_date=date(2026, 3, 1),
        rent_amount=Decimal("1000.00"),
        deposit_amount=Decimal("1000.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db_session.add_all([property_, unit, tenant, lease])
    await db_session.flush()

    generated = await generate_invoice(db_session, lease)
    repeated = await generate_invoice(db_session, lease)

    assert generated.id == repeated.id
    assert generated.amount_due == Decimal("548.39")


async def test_late_fee_sweep_applies_fee_only_once(db_session: AsyncSession, make_user) -> None:
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Late fee property",
        address_line1="2 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M2",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 2",
        bedrooms=1,
        bathrooms=1,
        market_rent=Decimal("1000.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        full_name="Late Fee Tenant",
        email="late-fee-service@example.com",
        phone="555-0101",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
        rent_amount=Decimal("1000.00"),
        deposit_amount=Decimal("1000.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db_session.add_all([property_, unit, tenant, lease])
    await db_session.flush()
    invoice = await generate_invoice(db_session, lease)

    due_date_sweep = await apply_late_fees(db_session, as_of=date(2026, 1, 1))
    first_sweep = await apply_late_fees(db_session, as_of=date(2026, 1, 2))
    second_sweep = await apply_late_fees(db_session, as_of=date(2026, 1, 2))
    await db_session.refresh(invoice)

    assert due_date_sweep == []
    assert [charged.id for charged in first_sweep] == [invoice.id]
    assert second_sweep == []
    assert invoice.amount_due == Decimal("1020.00")
    assert invoice.late_fee_amount == LATE_FEE_AMOUNT
    assert invoice.status is InvoiceStatus.OVERDUE
