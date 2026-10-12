from datetime import timedelta

import pytest
from jose import JWTError
from pydantic import SecretStr

from app.core.config import settings
from app.core.security import SecuritySettings
from app.services import auth

TEST_JWT_SECRET = "test-only-secret-with-at-least-32-characters"


@pytest.fixture
def configured_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "security",
        SecuritySettings(jwt_secret_key=SecretStr(TEST_JWT_SECRET)),
    )


def test_password_hash_verifies_and_is_not_plaintext() -> None:
    password = "correct horse battery staple"

    password_hash = auth.get_password_hash(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")
    assert auth.verify_password(password, password_hash)
    assert not auth.verify_password("incorrect password", password_hash)


def test_invalid_password_hash_returns_false() -> None:
    assert not auth.verify_password("password", "not-an-argon2-hash")


@pytest.mark.usefixtures("configured_jwt_secret")
def test_access_token_round_trip() -> None:
    token = auth.create_access_token({"sub": "user-123"})

    claims = auth.decode_access_token(token)

    assert claims.sub == "user-123"
    assert claims.exp.tzinfo is not None


@pytest.mark.usefixtures("configured_jwt_secret")
def test_expired_access_token_is_rejected() -> None:
    token = auth.create_access_token(
        {"sub": "user-123"},
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(JWTError):
        auth.decode_access_token(token)


@pytest.mark.usefixtures("configured_jwt_secret")
def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(JWTError):
        auth.decode_access_token("not-a-jwt")


def test_jwt_operations_fail_when_secret_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "security", SecuritySettings())

    with pytest.raises(RuntimeError, match="SECURITY__JWT_SECRET_KEY"):
        auth.create_access_token({"sub": "user-123"})


@pytest.mark.usefixtures("configured_jwt_secret")
def test_access_token_requires_subject() -> None:
    with pytest.raises(ValueError, match="'sub'"):
        auth.create_access_token({"user_id": "user-123"})
