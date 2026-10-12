from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import SecuritySettings
from app.db.database import get_db_session
from app.main import app
from app.models.company import Company
from app.models.user import User as UserModel

TEST_JWT_SECRET = "test-only-secret-with-at-least-32-characters"


class FakeUniqueViolation(Exception):
    constraint_name = "uq_users_email"


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.users: list[UserModel] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        companies = [item for item in self.added if isinstance(item, Company)]
        users = [item for item in self.added if isinstance(item, UserModel)]

        for user in users:
            if any(existing.email == user.email for existing in self.users):
                raise IntegrityError("INSERT users", {}, FakeUniqueViolation())

            company = user.company
            company.id = company.id or uuid4()
            user.id = user.id or uuid4()
            user.company_id = company.id
            user.created_at = datetime.now(timezone.utc)
            self.users.append(user)

        for company in companies:
            company.id = company.id or uuid4()
        self.added.clear()

    async def refresh(self, instance: object) -> None:
        del instance
        return None

    async def rollback(self) -> None:
        self.added.clear()

    async def execute(self, statement: object) -> SimpleNamespace:
        where_clause = getattr(statement, "whereclause")
        column_name = where_clause.left.name
        value = where_clause.right.value
        user = next(
            (item for item in self.users if getattr(item, column_name) == value),
            None,
        )
        return SimpleNamespace(scalar_one_or_none=lambda: user)

    async def get(self, model: type[UserModel], user_id: UUID) -> UserModel | None:
        return next(
            (
                user
                for user in self.users
                if isinstance(user, model) and user.id == user_id
            ),
            None,
        )


@pytest.fixture
def api_session(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FakeAsyncSession]:
    session = FakeAsyncSession()
    monkeypatch.setattr(
        settings,
        "security",
        SecuritySettings(jwt_secret_key=SecretStr(TEST_JWT_SECRET)),
    )

    async def override_get_db_session() -> AsyncIterator[FakeAsyncSession]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    yield session
    app.dependency_overrides.pop(get_db_session, None)


def test_register_login_and_read_current_user(api_session: FakeAsyncSession) -> None:
    with TestClient(app) as client:
        registration = client.post(
            "/register",
            json={
                "email": "OWNER@example.com",
                "password": "secure-password",
                "name": "Owner",
                "company_name": "Example Ltd",
                "company_email": "quotes@example.com",
                "company_phone": "+55 11 3333-4444",
            },
        )

        assert registration.status_code == 201
        assert "password_hash" not in registration.json()
        assert api_session.users[0].email_verified is True
        assert api_session.users[0].company.email == "quotes@example.com"
        assert api_session.users[0].company.phone == "+55 11 3333-4444"

        bad_login = client.post(
            "/token",
            data={
                "username": "owner@example.com",
                "password": "incorrect-password",
            },
        )
        api_session.users[0].email_verified = False
        login = client.post(
            "/token",
            data={
                "username": "owner@example.com",
                "password": "secure-password",
            },
        )

        assert bad_login.status_code == 401
        assert login.status_code == 200
        token = login.json()["access_token"]
        current_user = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert current_user.status_code == 200
    assert current_user.json()["id"] == str(api_session.users[0].id)
    assert current_user.json()["role"] == "owner"
    assert "password_hash" not in current_user.json()


def test_registration_requires_only_access_email_and_password(
    api_session: FakeAsyncSession,
) -> None:
    with TestClient(app) as client:
        registration = client.post(
            "/register",
            json={
                "email": "new-owner@example.com",
                "password": "secure-password",
            },
        )

    assert registration.status_code == 201
    assert api_session.users[0].name == "new-owner"
    assert api_session.users[0].company.name == "new-owner"
    assert api_session.users[0].company.email is None
    assert api_session.users[0].company.phone is None


@pytest.mark.usefixtures("api_session")
def test_duplicate_email_is_rejected_case_insensitively() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/register",
            json={"email": "same@example.com", "password": "secure-password"},
        )
        duplicate = client.post(
            "/register",
            json={"email": "SAME@example.com", "password": "secure-password"},
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409


@pytest.mark.usefixtures("api_session")
def test_bad_credentials_and_invalid_registration_data() -> None:
    with TestClient(app) as client:
        bad_credentials = client.post(
            "/token",
            data={"username": "missing@example.com", "password": "wrong-password"},
        )
        invalid_registration = client.post(
            "/register",
            json={"email": "not-an-email", "password": "short"},
        )

    assert bad_credentials.status_code == 401
    assert invalid_registration.status_code == 422


@pytest.mark.usefixtures("api_session")
def test_invalid_bearer_token_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
