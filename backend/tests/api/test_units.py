"""HTTP tests for owner-scoped unit endpoints."""

from __future__ import annotations

from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.property import Property, PropertyType
from app.models.unit import Unit, UnitStatus


async def _make_property(db_session: AsyncSession, owner_id) -> Property:
    property_ = Property(
        owner_id=owner_id,
        name="Unit test property",
        address_line1="1 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M1",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    db_session.add(property_)
    await db_session.flush()
    return property_


async def test_unit_crud_duplicate_label_and_filtering(db_session: AsyncSession, make_user) -> None:
    owner = await make_user()
    property_ = await _make_property(db_session, owner.id)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    payload = {
        "property_id": str(property_.id),
        "label": "Unit 1",
        "bedrooms": 2,
        "bathrooms": 1,
        "market_rent": "1800.00",
        "status": "vacant",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/units", json=payload, headers=headers)
            assert created.status_code == 201
            unit_id = created.json()["id"]

            duplicate = await client.post("/api/v1/units", json=payload, headers=headers)
            assert duplicate.status_code == 409
            assert duplicate.json() == {
                "detail": "A unit with this label already exists for this property"
            }

            filtered = await client.get(
                "/api/v1/units",
                params={"property_id": str(property_.id), "status": "vacant", "page_size": 1},
                headers=headers,
            )
            assert filtered.status_code == 200
            assert filtered.json()["total"] == 1
            assert filtered.json()["items"][0]["id"] == unit_id

            updated = await client.patch(
                f"/api/v1/units/{unit_id}",
                json={"label": "Unit 1A", "status": "occupied"},
                headers=headers,
            )
            assert updated.status_code == 200
            assert updated.json()["label"] == "Unit 1A"

            fetched = await client.get(f"/api/v1/units/{unit_id}", headers=headers)
            assert fetched.status_code == 200
            deleted = await client.delete(f"/api/v1/units/{unit_id}", headers=headers)
            assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()


async def test_units_do_not_leak_between_landlords(db_session: AsyncSession, make_user) -> None:
    owner = await make_user()
    other_owner = await make_user()
    property_ = await _make_property(db_session, owner.id)
    unit = Unit(
        property_id=property_.id,
        label="Hidden unit",
        bedrooms=1,
        bathrooms=1,
        market_rent=Decimal("1200.00"),
        status=UnitStatus.VACANT,
    )
    db_session.add(unit)
    await db_session.flush()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(other_owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            fetched = await client.get(f"/api/v1/units/{unit.id}", headers=headers)
            assert fetched.status_code == 404
            listed = await client.get("/api/v1/units", headers=headers)
            assert listed.status_code == 200
            assert listed.json()["items"] == []
            assert listed.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()
