"""HTTP tests for owner-scoped property endpoints."""

from __future__ import annotations

from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.property import PropertyType
from app.models.unit import Unit, UnitStatus

PROPERTY = {
    "name": "Maple House",
    "address_line1": "1 Main Street",
    "city": "Toronto",
    "region": "ON",
    "postal_code": "M1M 1M1",
    "country": "Canada",
    "property_type": PropertyType.SINGLE_FAMILY.value,
}


async def test_property_crud_and_unit_listing(db_session: AsyncSession, make_user) -> None:
    owner = await make_user()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/properties", json=PROPERTY, headers=headers)
            assert created.status_code == 201
            property_id = created.json()["id"]

            listed = await client.get("/api/v1/properties", headers=headers)
            assert listed.status_code == 200
            assert listed.json()["items"] == [created.json()]
            assert listed.json()["total"] == 1

            updated = await client.patch(
                f"/api/v1/properties/{property_id}",
                json={"name": "Updated House"},
                headers=headers,
            )
            assert updated.status_code == 200
            assert updated.json()["name"] == "Updated House"

            unit = Unit(
                property_id=property_id,
                label="Unit 1",
                bedrooms=2,
                bathrooms=1,
                market_rent=Decimal("1800.00"),
                status=UnitStatus.VACANT,
            )
            db_session.add(unit)
            await db_session.flush()

            units = await client.get(f"/api/v1/properties/{property_id}/units", headers=headers)
            assert units.status_code == 200
            assert units.json()["items"][0]["label"] == "Unit 1"

            deleted = await client.delete(f"/api/v1/properties/{property_id}", headers=headers)
            assert deleted.status_code == 204
            missing = await client.get(f"/api/v1/properties/{property_id}", headers=headers)
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_landlord_cannot_access_another_landlords_property(
    db_session: AsyncSession, make_user
) -> None:
    owner = await make_user()
    other_owner = await make_user()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    owner_headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/properties", json=PROPERTY, headers=owner_headers)
            property_id = created.json()["id"]

            for method, url, body in (
                ("get", f"/api/v1/properties/{property_id}", None),
                ("patch", f"/api/v1/properties/{property_id}", {"name": "Stolen"}),
                ("delete", f"/api/v1/properties/{property_id}", None),
                ("get", f"/api/v1/properties/{property_id}/units", None),
            ):
                response = await client.request(method, url, headers=other_headers, json=body)
                assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
