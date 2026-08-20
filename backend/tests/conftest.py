"""Pytest fixtures: test database, async client, auth headers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.db.session import engine
from app.models.user import User, UserRole


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A session bound to a single connection/transaction, rolled back after the test.

    Code under test may call `session.commit()` freely (e.g. `revoke_token`) — with
    `join_transaction_mode="create_savepoint"`, commits only release a savepoint;
    nothing is persisted past the outer rollback below.
    """
    async with engine.connect() as connection:
        await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with session_factory() as session:
            yield session
        await connection.rollback()


@pytest.fixture
async def make_user(db_session: AsyncSession):
    """Factory fixture: persist a User row with a real password hash."""

    async def _make_user(
        *,
        email: str | None = None,
        password: str = "correct horse battery staple",
        role: UserRole = UserRole.LANDLORD,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email or f"{uuid.uuid4()}@example.com",
            hashed_password=hash_password(password),
            full_name="Test User",
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    return _make_user
