"""Tests for Entra token authentication to Azure Database for PostgreSQL."""

from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import session


def test_each_new_connection_gets_a_fresh_entra_token() -> None:
    engine = create_async_engine("postgresql+asyncpg://id-rentflow-api-staging@db.example/rentflow")
    credential = MagicMock()
    credential.get_token.return_value.token = "entra-access-token"

    with patch("app.core.azure.get_azure_credential", return_value=credential):
        session.use_entra_token_auth(engine)
        cparams: dict[str, object] = {"user": "id-rentflow-api-staging"}
        engine.sync_engine.dialect.dispatch.do_connect(
            engine.sync_engine.dialect, MagicMock(), [], cparams
        )

    credential.get_token.assert_called_once_with(session.POSTGRES_ENTRA_SCOPE)
    assert cparams["password"] == "entra-access-token"


def test_entra_engines_recycle_connections_before_tokens_expire() -> None:
    settings = MagicMock(database_entra_auth=True)
    with (
        patch.object(session, "get_settings", return_value=settings),
        patch.object(session, "use_entra_token_auth") as hook,
    ):
        engine = session.build_engine("postgresql+asyncpg://user@db.example/rentflow")

    hook.assert_called_once_with(engine)
    assert engine.pool._recycle == session.ENTRA_POOL_RECYCLE_SECONDS


def test_password_engines_are_left_alone() -> None:
    settings = MagicMock(database_entra_auth=False)
    with (
        patch.object(session, "get_settings", return_value=settings),
        patch.object(session, "use_entra_token_auth") as hook,
    ):
        engine = session.build_engine("postgresql+asyncpg://rentflow:rentflow@db/rentflow")

    hook.assert_not_called()
    assert engine.pool._recycle == -1
