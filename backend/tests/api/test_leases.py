"""HTTP tests for lease creation and lifecycle transitions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.lease import Lease, LeaseStatus
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus


async def _lease_fixture(db_session: AsyncSession, make_user):
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Lease property",
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
    tenant = Tenant(full_name="Lease Tenant", email="lease@example.com", phone="555-0100")
    db_session.add_all([property_, unit, tenant])
    await db_session.flush()
    return owner, unit, tenant


def _payload(unit_id, tenant_id, *, status="draft", start="2026-01-01", end="2027-01-01"):
    return {
        "unit_id": str(unit_id),
        "tenant_id": str(tenant_id),
        "start_date": start,
        "end_date": end,
        "rent_amount": "1800.00",
        "deposit_amount": "1800.00",
        "billing_day": 1,
        "status": status,
    }


async def test_create_activate_and_overlap_returns_documented_conflict(
    db_session: AsyncSession, make_user
) -> None:
    owner, unit, tenant = await _lease_fixture(db_session, make_user)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/leases",
                json=_payload(unit.id, tenant.id),
                headers=headers,
            )
            assert created.status_code == 201
            lease_id = created.json()["id"]
            activated = await client.post(f"/api/v1/leases/{lease_id}/activate", headers=headers)
            assert activated.status_code == 200
            assert activated.json()["status"] == "active"

            overlap = await client.post(
                "/api/v1/leases",
                json=_payload(
                    unit.id, tenant.id, status="active", start="2026-06-01", end="2027-06-01"
                ),
                headers=headers,
            )
            assert overlap.status_code == 409
            assert overlap.json() == {
                "detail": "Lease overlaps an active lease for this unit",
                "code": "lease_overlap",
            }
    finally:
        app.dependency_overrides.clear()


async def test_renew_creates_successor_without_mutating_original(
    db_session: AsyncSession, make_user
) -> None:
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    original = Lease(
        unit_id=unit.id,
        tenant_id=tenant.id,
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        rent_amount=Decimal("1800.00"),
        deposit_amount=Decimal("1800.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db_session.add(original)
    await db_session.flush()
    original_id = original.id

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/leases/{original_id}/renew",
                json={"start_date": "2027-01-01", "end_date": "2028-01-01"},
                headers=headers,
            )
            assert response.status_code == 200
            successor = response.json()
            assert successor["id"] != str(original_id)
            assert successor["status"] == "draft"
            assert successor["start_date"] == "2027-01-01"
            assert successor["end_date"] == "2028-01-01"
            assert original.start_date == date(2026, 1, 1)
            assert original.end_date == date(2027, 1, 1)
    finally:
        app.dependency_overrides.clear()


async def test_termination_requires_early_date_and_cannot_be_reactivated(
    db_session: AsyncSession, make_user
) -> None:
    owner, unit, tenant = await _lease_fixture(db_session, make_user)
    lease = Lease(
        unit_id=unit.id,
        tenant_id=tenant.id,
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        rent_amount=Decimal("1800.00"),
        deposit_amount=Decimal("1800.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db_session.add(lease)
    await db_session.flush()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            terminated = await client.post(
                f"/api/v1/leases/{lease.id}/terminate",
                json={"reason": "Owner move", "end_date": "2026-06-30"},
                headers=headers,
            )
            assert terminated.status_code == 200
            assert terminated.json()["status"] == "terminated"
            assert terminated.json()["end_date"] == "2026-06-30"

            reactivated = await client.post(f"/api/v1/leases/{lease.id}/activate", headers=headers)
            assert reactivated.status_code == 409
    finally:
        app.dependency_overrides.clear()
