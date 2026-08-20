"""Registration endpoint tests."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, decode_token
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
    db_session: AsyncSession,
    make_user,
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


async def test_login_returns_token_pair(db_session: AsyncSession, make_user) -> None:
    user = await make_user(email="login@example.com", password="correct-password")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "correct-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_token(body["access_token"], expected_type="access")["sub"] == str(user.id)
    assert decode_token(body["refresh_token"], expected_type="refresh")["sub"] == str(user.id)


async def test_login_rejects_invalid_credentials(db_session: AsyncSession, make_user) -> None:
    user = await make_user(email="login-failure@example.com", password="correct-password")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "incorrect-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


async def test_refresh_rotates_token(db_session: AsyncSession, make_user) -> None:
    user = await make_user()
    old_refresh_token = create_refresh_token(str(user.id))

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
            )
            reused = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["refresh_token"] != old_refresh_token
    assert reused.status_code == 401


async def test_refresh_rejects_access_token() -> None:
    access_token = create_access_token("d004228b-dad7-4c5c-86f1-92e8fef8f772")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


async def test_logout_revokes_refresh_token(db_session: AsyncSession, make_user) -> None:
    user = await make_user()
    refresh_token = create_refresh_token(str(user.id))

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            logout_response = await client.post(
                "/api/v1/auth/logout", json={"refresh_token": refresh_token}
            )
            refresh_response = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
            )
    finally:
        app.dependency_overrides.clear()

    assert logout_response.status_code == 204
    assert refresh_response.status_code == 401
    assert refresh_response.json() == {"detail": "Refresh token has been revoked"}


async def test_me_returns_current_user(db_session: AsyncSession, make_user) -> None:
    user = await make_user(email="current-user@example.com")
    access_token = create_access_token(str(user.id))

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert "hashed_password" not in response.json()


async def test_me_rejects_missing_access_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
