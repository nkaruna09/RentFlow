"""HTTP tests for owner-scoped invoices, payments, and arrears."""

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


async def _lease_fixture(db: AsyncSession, make_user):
    owner = await make_user()
    property_ = Property(
        owner_id=owner.id,
        name="Payment property",
        address_line1="4 Main Street",
        city="Toronto",
        region="ON",
        postal_code="M1M 1M4",
        country="Canada",
        property_type=PropertyType.SINGLE_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 4",
        bedrooms=1,
        bathrooms=1,
        market_rent=Decimal("1000.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        full_name="Payment Tenant",
        email="payment-tenant@example.com",
        phone="555-0103",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 1),
        rent_amount=Decimal("1000.00"),
        deposit_amount=Decimal("1000.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db.add_all([property_, unit, tenant, lease])
    await db.flush()
    return owner, lease


def _invoice_payload(lease_id) -> dict[str, str]:
    return {
        "lease_id": str(lease_id),
        "period_start": "2026-01-01",
        "period_end": "2026-02-01",
        "amount_due": "100.00",
        "due_date": "2026-01-01",
    }


async def test_partial_payment_updates_status_and_arrears(
    db_session: AsyncSession, make_user
) -> None:
    owner, lease = await _lease_fixture(db_session, make_user)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/payments/invoices",
                json=_invoice_payload(lease.id),
                headers=headers,
            )
            assert created.status_code == 201
            invoice_id = created.json()["id"]

            listed = await client.get("/api/v1/payments/invoices", headers=headers)
            retrieved = await client.get(f"/api/v1/payments/invoices/{invoice_id}", headers=headers)
            assert listed.status_code == 200
            assert listed.json()["total"] == 1
            assert retrieved.status_code == 200

            partial = await client.post(
                f"/api/v1/payments/invoices/{invoice_id}/payments",
                json={
                    "amount": "40.00",
                    "paid_at": "2026-01-02T12:00:00Z",
                    "method": "bank_transfer",
                },
                headers=headers,
            )
            assert partial.status_code == 201

            after_partial = await client.get(
                f"/api/v1/payments/invoices/{invoice_id}", headers=headers
            )
            assert after_partial.json()["status"] == "partial"

            arrears = await client.get("/api/v1/payments/arrears", headers=headers)
            assert arrears.status_code == 200
            assert arrears.json()["items"] == [
                {"lease_id": str(lease.id), "outstanding_balance": "60.00"}
            ]
            assert arrears.json()["outstanding_total"] == "60.00"

            paid = await client.post(
                f"/api/v1/payments/invoices/{invoice_id}/payments",
                json={
                    "amount": "60.00",
                    "paid_at": "2026-01-03T12:00:00Z",
                    "method": "bank_transfer",
                },
                headers=headers,
            )
            assert paid.status_code == 201
            after_paid = await client.get(
                f"/api/v1/payments/invoices/{invoice_id}", headers=headers
            )
            assert after_paid.json()["status"] == "paid"
    finally:
        app.dependency_overrides.clear()


async def test_invoices_are_not_visible_to_another_owner(
    db_session: AsyncSession, make_user
) -> None:
    owner, lease = await _lease_fixture(db_session, make_user)
    other_owner = await make_user()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    owner_headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(str(other_owner.id))}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/payments/invoices",
                json=_invoice_payload(lease.id),
                headers=owner_headers,
            )
            invoice_id = created.json()["id"]

            hidden = await client.get(
                f"/api/v1/payments/invoices/{invoice_id}", headers=other_headers
            )
            hidden_payment = await client.post(
                f"/api/v1/payments/invoices/{invoice_id}/payments",
                json={
                    "amount": "10.00",
                    "paid_at": "2026-01-02T12:00:00Z",
                    "method": "cash",
                },
                headers=other_headers,
            )

            assert hidden.status_code == 404
            assert hidden_payment.status_code == 404
    finally:
        app.dependency_overrides.clear()
