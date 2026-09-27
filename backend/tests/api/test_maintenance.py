"""HTTP tests for scoped maintenance requests, workflow updates, and comments."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
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


async def _maintenance_fixture(
    db: AsyncSession,
    make_user,
    *,
    manager_role: UserRole = UserRole.LANDLORD,
):
    manager = await make_user(role=manager_role)
    tenant_user = await make_user(role=UserRole.TENANT)
    other_tenant_user = await make_user(role=UserRole.TENANT)
    property_ = Property(
        owner_id=manager.id,
        name="Maintenance property",
        address_line1="9 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M9",
        country="Canada",
        property_type=PropertyType.MULTI_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 9",
        bedrooms=Decimal("2"),
        bathrooms=Decimal("1"),
        market_rent=Decimal("1800.00"),
        status=UnitStatus.OCCUPIED,
    )
    other_unit = Unit(
        property=property_,
        label="Unit 10",
        bedrooms=Decimal("1"),
        bathrooms=Decimal("1"),
        market_rent=Decimal("1500.00"),
        status=UnitStatus.VACANT,
    )
    tenant = Tenant(
        user_id=tenant_user.id,
        full_name="Maintenance Tenant",
        email="maintenance@example.com",
        phone="555-0109",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        rent_amount=Decimal("1800.00"),
        deposit_amount=Decimal("1800.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db.add_all([property_, unit, other_unit, tenant, lease])
    await db.flush()
    return manager, tenant_user, other_tenant_user, unit, other_unit


def _headers(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def _payload(unit_id) -> dict[str, str]:
    return {
        "unit_id": str(unit_id),
        "title": "Leaking faucet",
        "description": "The kitchen faucet is dripping continuously.",
        "priority": "high",
    }


@pytest.mark.parametrize("manager_role", [UserRole.LANDLORD, UserRole.MANAGER])
async def test_tenant_submission_filters_manager_workflow_and_comments(
    db_session: AsyncSession,
    make_user,
    manager_role: UserRole,
) -> None:
    manager, tenant_user, _, unit, _ = await _maintenance_fixture(
        db_session, make_user, manager_role=manager_role
    )

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/maintenance",
                json=_payload(unit.id),
                headers=_headers(tenant_user.id),
            )
            assert created.status_code == 201
            request_id = created.json()["id"]
            assert created.json()["reported_by"] == str(tenant_user.id)
            assert created.json()["status"] == "open"

            filtered = await client.get(
                "/api/v1/maintenance",
                params={"unit_id": str(unit.id), "status": "open", "priority": "high"},
                headers=_headers(manager.id),
            )
            no_matches = await client.get(
                "/api/v1/maintenance",
                params={"priority": "low"},
                headers=_headers(manager.id),
            )
            assert filtered.status_code == 200
            assert filtered.json()["total"] == 1
            assert no_matches.json()["total"] == 0

            invalid = await client.patch(
                f"/api/v1/maintenance/{request_id}",
                json={"status": "closed"},
                headers=_headers(manager.id),
            )
            assert invalid.status_code == 409
            assert invalid.json() == {
                "detail": "Invalid maintenance status transition from 'open' to 'closed'",
                "code": "invalid_maintenance_status_transition",
            }

            assigned = await client.patch(
                f"/api/v1/maintenance/{request_id}",
                json={"assigned_to": str(manager.id)},
                headers=_headers(manager.id),
            )
            assert assigned.status_code == 200
            assert assigned.json()["assigned_to"] == str(manager.id)
            assert assigned.json()["status"] == "assigned"

            comment = await client.post(
                f"/api/v1/maintenance/{request_id}/comments",
                json={"body": "The leak is getting worse."},
                headers=_headers(tenant_user.id),
            )
            assert comment.status_code == 201
            assert comment.json()["request_id"] == request_id
            assert comment.json()["author_id"] == str(tenant_user.id)

            fetched = await client.get(
                f"/api/v1/maintenance/{request_id}",
                headers=_headers(tenant_user.id),
            )
            assert fetched.status_code == 200
            assert fetched.json()["status"] == "assigned"
    finally:
        app.dependency_overrides.clear()


async def test_tenant_cannot_access_requests_or_units_outside_active_lease(
    db_session: AsyncSession,
    make_user,
) -> None:
    manager, tenant_user, other_tenant_user, unit, other_unit = await _maintenance_fixture(
        db_session, make_user
    )

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/maintenance",
                json=_payload(unit.id),
                headers=_headers(tenant_user.id),
            )
            request_id = created.json()["id"]

            hidden = await client.get(
                f"/api/v1/maintenance/{request_id}",
                headers=_headers(other_tenant_user.id),
            )
            hidden_comment = await client.post(
                f"/api/v1/maintenance/{request_id}/comments",
                json={"body": "I should not see this request."},
                headers=_headers(other_tenant_user.id),
            )
            wrong_unit = await client.post(
                "/api/v1/maintenance",
                json=_payload(other_unit.id),
                headers=_headers(tenant_user.id),
            )
            tenant_patch = await client.patch(
                f"/api/v1/maintenance/{request_id}",
                json={"priority": "emergency"},
                headers=_headers(tenant_user.id),
            )

            assert hidden.status_code == 404
            assert hidden_comment.status_code == 404
            assert wrong_unit.status_code == 404
            assert tenant_patch.status_code == 403

            manager_view = await client.get(
                f"/api/v1/maintenance/{request_id}", headers=_headers(manager.id)
            )
            assert manager_view.status_code == 200
    finally:
        app.dependency_overrides.clear()
