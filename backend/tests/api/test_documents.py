"""HTTP tests for document upload, listing, download and access scoping."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.lease import Lease, LeaseStatus
from app.models.maintenance import MaintenancePriority, MaintenanceRequest
from app.models.property import Property, PropertyType
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitStatus
from app.models.user import UserRole
from app.services import storage_service

PDF = b"%PDF-1.7 test document"


async def _fixture(db: AsyncSession, make_user):
    landlord = await make_user(role=UserRole.LANDLORD)
    tenant_user = await make_user(role=UserRole.TENANT)
    outsider = await make_user(role=UserRole.LANDLORD)
    property_ = Property(
        owner_id=landlord.id,
        name="Document property",
        address_line1="1 Paper Street",
        city="Hamilton",
        region="ON",
        postal_code="L8S 4L8",
        country="Canada",
        property_type=PropertyType.MULTI_FAMILY,
    )
    unit = Unit(
        property=property_,
        label="Unit 1",
        bedrooms=Decimal("1"),
        bathrooms=Decimal("1"),
        market_rent=Decimal("1500.00"),
        status=UnitStatus.OCCUPIED,
    )
    tenant = Tenant(
        user_id=tenant_user.id,
        full_name="Document Tenant",
        email="documents@example.com",
        phone="555-0101",
    )
    lease = Lease(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        rent_amount=Decimal("1500.00"),
        deposit_amount=Decimal("1500.00"),
        billing_day=1,
        status=LeaseStatus.ACTIVE,
    )
    db.add_all([property_, unit, tenant, lease])
    await db.flush()
    request = MaintenanceRequest(
        unit_id=unit.id,
        reported_by=tenant_user.id,
        title="Broken window",
        description="Cracked pane in the bedroom.",
        priority=MaintenancePriority.HIGH,
    )
    db.add(request)
    await db.flush()
    return landlord, tenant_user, outsider, lease, request


def _headers(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def _fake_storage():
    blobs: dict[str, bytes] = {}

    async def upload(name: str, data: bytes, _content_type: str) -> str:
        blobs[name] = data
        return f"https://strentflowtest.blob.core.windows.net/rentflow-documents/{name}"

    async def download(name: str) -> bytes:
        return blobs[name]

    return blobs, upload, download


async def test_lease_documents_are_scoped_to_the_lease(db_session: AsyncSession, make_user) -> None:
    landlord, tenant_user, outsider, lease, _ = await _fixture(db_session, make_user)
    blobs, upload, download = _fake_storage()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with (
            patch.object(storage_service, "upload", upload),
            patch.object(storage_service, "download", download),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                form = {"owner_type": "lease", "owner_id": str(lease.id)}
                file = {"file": ("Signed lease.pdf", PDF, "application/pdf")}

                tenant_upload = await client.post(
                    "/api/v1/documents", data=form, files=file, headers=_headers(tenant_user.id)
                )
                assert tenant_upload.status_code == 403

                created = await client.post(
                    "/api/v1/documents", data=form, files=file, headers=_headers(landlord.id)
                )
                assert created.status_code == 201
                body = created.json()
                assert body["filename"] == "Signed lease.pdf"
                assert body["size_bytes"] == len(PDF)
                assert "blob_url" not in body
                assert list(blobs) == [f"lease/{lease.id}/{body['id']}/Signed_lease.pdf"]

                listed = await client.get(
                    "/api/v1/documents",
                    params=form,
                    headers=_headers(tenant_user.id),
                )
                assert listed.status_code == 200
                assert [item["id"] for item in listed.json()["items"]] == [body["id"]]

                content = await client.get(
                    f"/api/v1/documents/{body['id']}/content", headers=_headers(tenant_user.id)
                )
                assert content.status_code == 200
                assert content.content == PDF
                assert content.headers["content-type"] == "application/pdf"
                assert "attachment" in content.headers["content-disposition"]

                hidden_list = await client.get(
                    "/api/v1/documents", params=form, headers=_headers(outsider.id)
                )
                hidden_content = await client.get(
                    f"/api/v1/documents/{body['id']}/content", headers=_headers(outsider.id)
                )
                assert hidden_list.status_code == 404
                assert hidden_content.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_tenants_can_attach_photos_to_their_maintenance_requests(
    db_session: AsyncSession, make_user
) -> None:
    _, tenant_user, outsider, _, request = await _fixture(db_session, make_user)
    _, upload, _ = _fake_storage()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(storage_service, "upload", upload):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                form = {"owner_type": "maintenance_request", "owner_id": str(request.id)}
                photo = {"file": ("window.png", b"\x89PNG data", "image/png")}

                created = await client.post(
                    "/api/v1/documents", data=form, files=photo, headers=_headers(tenant_user.id)
                )
                assert created.status_code == 201

                outsider_upload = await client.post(
                    "/api/v1/documents", data=form, files=photo, headers=_headers(outsider.id)
                )
                assert outsider_upload.status_code == 404

                executable = await client.post(
                    "/api/v1/documents",
                    data=form,
                    files={"file": ("run.sh", b"#!/bin/sh", "application/x-sh")},
                    headers=_headers(tenant_user.id),
                )
                assert executable.status_code == 400
    finally:
        app.dependency_overrides.clear()


async def test_receipts_are_hidden_from_tenants_and_missing_payments(
    db_session: AsyncSession, make_user
) -> None:
    landlord, tenant_user, *_ = await _fixture(db_session, make_user)
    upload = AsyncMock()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(storage_service, "upload", upload):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                form = {"owner_type": "payment", "owner_id": str(uuid4())}
                receipt = {"file": ("receipt.pdf", PDF, "application/pdf")}
                for user in (tenant_user, landlord):
                    response = await client.post(
                        "/api/v1/documents", data=form, files=receipt, headers=_headers(user.id)
                    )
                    assert response.status_code == 404
        upload.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()
