"""Service-layer tests for lease overlap and lifecycle boundary conditions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationError
from app.models.lease import Lease, LeaseStatus
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.services import lease_service


async def _lease_fixture(db_session: AsyncSession, make_user):
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Lease service property",
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
        bedrooms=2,
        bathrooms=1,
        market_rent=Decimal("1800.00"),
        status=UnitStatus.VACANT,
    )
    tenant = Tenant(full_name="Lease Tenant", email="lease-service@example.com", phone="555-0100")
    db_session.add_all([property_, unit, tenant])
    await db_session.flush()
    return owner, unit, tenant


def _values(
    unit_id: UUID,
    tenant_id: UUID,
    *,
    start: date,
    end: date,
    status: LeaseStatus = LeaseStatus.ACTIVE,
) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "tenant_id": tenant_id,
        "start_date": start,
        "end_date": end,
        "rent_amount": Decimal("1800.00"),
        "deposit_amount": Decimal("1800.00"),
        "billing_day": 1,
        "status": status,
    }


@pytest.mark.asyncio
async def test_overlapping_active_leases_are_rejected(db_session: AsyncSession, make_user) -> None:
    """The Postgres exclusion constraint rejects intersecting active ranges."""
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    unit_id = unit.id
    tenant_id = tenant.id
    await lease_service.create_lease(
        db_session,
        owner,
        _values(unit_id, tenant_id, start=date(2026, 1, 1), end=date(2027, 1, 1)),
    )

    with pytest.raises(ConflictError) as overlap:
        await lease_service.create_lease(
            db_session,
            owner,
            _values(unit_id, tenant_id, start=date(2026, 6, 1), end=date(2027, 6, 1)),
        )

    assert overlap.value.detail == lease_service.OVERLAP_DETAIL
    assert overlap.value.code == "lease_overlap"


@pytest.mark.asyncio
async def test_back_to_back_active_leases_are_allowed(db_session: AsyncSession, make_user) -> None:
    """The [start, end) range permits a successor on the prior end date."""
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    first_end = date(2027, 1, 1)
    await lease_service.create_lease(
        db_session,
        owner,
        _values(unit.id, tenant.id, start=date(2026, 1, 1), end=first_end),
    )

    successor = await lease_service.create_lease(
        db_session,
        owner,
        _values(unit.id, tenant.id, start=first_end, end=date(2028, 1, 1)),
    )
    assert successor.status is LeaseStatus.ACTIVE
    assert successor.start_date == first_end


@pytest.mark.asyncio
async def test_renewal_creates_successor_and_preserves_original_history(
    db_session: AsyncSession, make_user
) -> None:
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    original = await lease_service.create_lease(
        db_session,
        owner,
        _values(unit.id, tenant.id, start=date(2026, 1, 1), end=date(2027, 1, 1)),
    )

    successor = await lease_service.renew_lease(
        db_session,
        original.id,
        owner,
        {"start_date": date(2027, 1, 1), "end_date": date(2028, 1, 1)},
    )

    persisted_original = await db_session.get(Lease, original.id)
    assert persisted_original is not None
    assert successor.id != original.id
    assert successor.status is LeaseStatus.DRAFT
    assert successor.start_date == date(2027, 1, 1)
    assert successor.end_date == date(2028, 1, 1)
    assert persisted_original.status is LeaseStatus.ACTIVE
    assert persisted_original.start_date == date(2026, 1, 1)
    assert persisted_original.end_date == date(2027, 1, 1)


@pytest.mark.asyncio
async def test_termination_requires_reason_and_prevents_reactivation(
    db_session: AsyncSession, make_user
) -> None:
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    lease = await lease_service.create_lease(
        db_session,
        owner,
        _values(unit.id, tenant.id, start=date(2026, 1, 1), end=date(2027, 1, 1)),
    )

    with pytest.raises(ValidationError, match="Termination reason is required"):
        await lease_service.terminate_lease(
            db_session,
            lease.id,
            owner,
            reason="  ",
            end_date=date(2026, 6, 30),
        )

    terminated = await lease_service.terminate_lease(
        db_session,
        lease.id,
        owner,
        reason="Owner move",
        end_date=date(2026, 6, 30),
    )
    assert terminated.status is LeaseStatus.TERMINATED
    assert terminated.end_date == date(2026, 6, 30)

    with pytest.raises(ConflictError, match="Only draft leases can be activated"):
        await lease_service.activate_lease(db_session, lease.id, owner)
