"""Registration endpoint tests."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app


async def test_register_creates_user_without_exposing_password(
    db_session: AsyncSession,
) -> None:
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "new-user@example.com",
                    "password": "strong-password",
                    "full_name": "New User",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["role"] == "landlord"
    assert response.json()["email"] == "new-user@example.com"
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


async def test_register_rejects_duplicate_email(
    db_session: AsyncSession, make_user,
) -> None:
    await make_user(email="duplicate@example.com")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "DUPLICATE@example.com",
                    "password": "strong-password",
                    "full_name": "Duplicate User",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists"}


async def test_register_validation_errors_use_field_errors_shape() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "short", "full_name": ""},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert set(body["field_errors"]) == {"email", "password", "full_name"}
