"""Database-level constraints for the core rental domain."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.lease import Lease, LeaseStatus
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus


async def test_database_rejects_overlapping_active_leases(db_session, make_user) -> None:
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Test property",
        address_line1="1 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M1",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    tenant = Tenant(full_name="Test Tenant", email="tenant@example.com", phone="555-0100")
    db_session.add_all([property_, tenant])
    await db_session.flush()

    unit = Unit(
        property_id=property_.id,
        label="Unit 1",
        bedrooms=2,
        bathrooms=1,
        market_rent=Decimal("1800.00"),
        status=UnitStatus.VACANT,
    )
    db_session.add(unit)
    await db_session.flush()

    db_session.add(
        Lease(
            unit_id=unit.id,
            tenant_id=tenant.id,
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
            rent_amount=Decimal("1800.00"),
            deposit_amount=Decimal("1800.00"),
            billing_day=1,
            status=LeaseStatus.ACTIVE,
        )
    )
    await db_session.flush()

    db_session.add(
        Lease(
            unit_id=unit.id,
            tenant_id=tenant.id,
            start_date=date(2026, 6, 1),
            end_date=date(2027, 6, 1),
            rent_amount=Decimal("1900.00"),
            deposit_amount=Decimal("1900.00"),
            billing_day=1,
            status=LeaseStatus.ACTIVE,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
