"""HTTP tests for tenant visibility and lease history."""

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
from app.models.user import UserRole


async def _make_tenant_fixture(db_session: AsyncSession, make_user):
    owner = await make_user(role=UserRole.LANDLORD)
    tenant_user = await make_user(role=UserRole.TENANT)
    other_owner = await make_user(role=UserRole.LANDLORD)
    property_ = Property(
        owner_id=owner.id,
        name="Tenant property",
        address_line1="1 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M1",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    db_session.add(property_)
    await db_session.flush()
    unit = Unit(
        property_id=property_.id,
        label="Unit 1",
        bedrooms=2,
        bathrooms=1,
        market_rent=Decimal("1800.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        user_id=tenant_user.id,
        full_name="Tenant User",
        email="tenant@example.com",
        phone="555-0100",
    )
    db_session.add_all([unit, tenant])
    await db_session.flush()
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
    return owner, tenant_user, other_owner, tenant


async def test_tenants_are_visible_to_property_owner_and_linked_user(
    db_session: AsyncSession, make_user
) -> None:
    owner, tenant_user, other_owner, tenant = await _make_tenant_fixture(db_session, make_user)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for user in (owner, tenant_user):
                response = await client.get("/api/v1/tenants", headers=headers(user))
                assert response.status_code == 200
                assert response.json()["total"] == 1
                assert response.json()["items"][0]["id"] == str(tenant.id)

            owner_history = await client.get(
                f"/api/v1/tenants/{tenant.id}/leases", headers=headers(owner)
            )
            tenant_history = await client.get(
                f"/api/v1/tenants/{tenant.id}/leases", headers=headers(tenant_user)
            )
            assert owner_history.status_code == tenant_history.status_code == 200
            assert owner_history.json()["total"] == tenant_history.json()["total"] == 1

            hidden = await client.get(f"/api/v1/tenants/{tenant.id}", headers=headers(other_owner))
            hidden_history = await client.get(
                f"/api/v1/tenants/{tenant.id}/leases", headers=headers(other_owner)
            )
            assert hidden.status_code == hidden_history.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_landlord_can_update_and_delete_visible_tenant(
    db_session: AsyncSession, make_user
) -> None:
    owner, _, _, tenant = await _make_tenant_fixture(db_session, make_user)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            updated = await client.patch(
                f"/api/v1/tenants/{tenant.id}",
                json={"phone": "555-0199"},
                headers=headers,
            )
            assert updated.status_code == 200
            assert updated.json()["phone"] == "555-0199"

            deleted = await client.delete(f"/api/v1/tenants/{tenant.id}", headers=headers)
            assert deleted.status_code == 409
            assert deleted.json() == {"detail": "Cannot delete a tenant with lease history"}
    finally:
        app.dependency_overrides.clear()
