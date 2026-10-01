"""Async engine and session factory for PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# OAuth scope for Azure Database for PostgreSQL Entra authentication.
POSTGRES_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
# Recycle pooled connections well inside the ~60-90 minute token lifetime.
ENTRA_POOL_RECYCLE_SECONDS = 30 * 60


def use_entra_token_auth(engine: AsyncEngine) -> None:
    """Supply a fresh Entra access token as the password for each new connection.

    The credential caches tokens and refreshes them shortly before expiry, so
    this costs a network call roughly once an hour, not once per connection.
    """
    from app.core.azure import get_azure_credential

    @event.listens_for(engine.sync_engine, "do_connect")
    def _provide_token(_dialect: Any, _conn_rec: Any, _cargs: Any, cparams: dict[str, Any]) -> None:
        cparams["password"] = get_azure_credential().get_token(POSTGRES_ENTRA_SCOPE).token


def build_engine(url: str, **kwargs: Any) -> AsyncEngine:
    if get_settings().database_entra_auth:
        kwargs.setdefault("pool_recycle", ENTRA_POOL_RECYCLE_SECONDS)
    new_engine = create_async_engine(url, **kwargs)
    if get_settings().database_entra_auth:
        use_entra_token_auth(new_engine)
    return new_engine


settings = get_settings()
engine = build_engine(settings.database_url, future=True, pool_pre_ping=True)
async_session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def database_is_healthy() -> bool:
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    return True
