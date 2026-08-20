"""Unit tests for app.core.security: hashing, JWT issuance/verification, get_current_user."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)

settings = get_settings()


class TestPasswordHashing:
    def test_hash_is_not_the_plaintext(self) -> None:
        hashed = hash_password("hunter2")
        assert hashed != "hunter2"

    def test_verify_password_accepts_correct_password(self) -> None:
        hashed = hash_password("hunter2")
        assert verify_password("hunter2", hashed) is True

    def test_verify_password_rejects_incorrect_password(self) -> None:
        hashed = hash_password("hunter2")
        assert verify_password("wrong-password", hashed) is False


class TestTokenRoundTrip:
    def test_access_token_round_trips(self) -> None:
        subject = str(uuid.uuid4())
        token = create_access_token(subject)

        payload = decode_token(token, expected_type="access")

        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert "jti" in payload

    def test_refresh_token_round_trips(self) -> None:
        subject = str(uuid.uuid4())
        token = create_refresh_token(subject)

        payload = decode_token(token, expected_type="refresh")

        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh_token(self) -> None:
        token = create_access_token(str(uuid.uuid4()))

        with pytest.raises(AuthenticationError):
            decode_token(token, expected_type="refresh")


class TestExpiredToken:
    def test_expired_token_is_rejected(self) -> None:
        now = datetime.now(UTC)
        expired_token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "type": "access",
                "jti": str(uuid.uuid4()),
                "iat": now - timedelta(minutes=10),
                "exp": now - timedelta(minutes=1),
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        with pytest.raises(AuthenticationError, match="expired"):
            decode_token(expired_token, expected_type="access")


class TestTamperedToken:
    def test_token_signed_with_a_different_key_is_rejected(self) -> None:
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "type": "access", "jti": str(uuid.uuid4())},
            "not-the-real-secret-key",
            algorithm=settings.algorithm,
        )

        with pytest.raises(AuthenticationError):
            decode_token(token, expected_type="access")

    def test_modified_payload_is_rejected(self) -> None:
        token = create_access_token(str(uuid.uuid4()))
        header, payload, signature = token.split(".")
        tampered = f"{header}.{payload}x.{signature}"

        with pytest.raises(AuthenticationError):
            decode_token(tampered, expected_type="access")


class TestGetCurrentUser:
    async def test_returns_the_user_for_a_valid_token(self, db_session, make_user) -> None:
        user = await make_user()
        token = create_access_token(str(user.id))

        resolved = await get_current_user(token=token, db=db_session)

        assert resolved.id == user.id

    async def test_rejects_a_missing_token(self, db_session) -> None:
        with pytest.raises(AuthenticationError):
            await get_current_user(token=None, db=db_session)

    async def test_rejects_a_refresh_token(self, db_session, make_user) -> None:
        user = await make_user()
        token = create_refresh_token(str(user.id))

        with pytest.raises(AuthenticationError):
            await get_current_user(token=token, db=db_session)

    async def test_rejects_an_inactive_user(self, db_session, make_user) -> None:
        user = await make_user(is_active=False)
        token = create_access_token(str(user.id))

        with pytest.raises(AuthenticationError):
            await get_current_user(token=token, db=db_session)

    async def test_rejects_a_revoked_token(self, db_session, make_user) -> None:
        user = await make_user()
        token = create_access_token(str(user.id))
        payload = decode_token(token, expected_type="access")

        assert await is_token_revoked(db_session, uuid.UUID(payload["jti"])) is False

        await revoke_token(
            db_session,
            jti=uuid.UUID(payload["jti"]),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

        assert await is_token_revoked(db_session, uuid.UUID(payload["jti"])) is True
        with pytest.raises(AuthenticationError, match="revoked"):
            await get_current_user(token=token, db=db_session)
