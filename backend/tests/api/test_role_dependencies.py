"""HTTP-level tests for role-based endpoint dependencies."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import require_role
from app.core.exceptions import register_exception_handlers
from app.core.security import get_current_user
from app.models.user import User, UserRole

landlord_only_role = require_role(UserRole.LANDLORD)


async def test_tenant_gets_403_from_landlord_only_endpoint(make_user) -> None:
    tenant = await make_user(role=UserRole.TENANT)
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/landlord-only")
    async def landlord_only(
        current_user: User = Depends(landlord_only_role),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    test_app.dependency_overrides[get_current_user] = lambda: tenant
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/landlord-only")

    assert response.status_code == 403
    assert response.json() == {"detail": "Your role does not permit this action"}


async def test_landlord_can_use_landlord_only_endpoint(make_user) -> None:
    landlord = await make_user(role=UserRole.LANDLORD)
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/landlord-only")
    async def landlord_only(
        current_user: User = Depends(landlord_only_role),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    test_app.dependency_overrides[get_current_user] = lambda: landlord
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/landlord-only")

    assert response.status_code == 200
    assert response.json() == {"user_id": str(landlord.id)}
