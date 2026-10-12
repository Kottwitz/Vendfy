from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.routes.auth import get_current_user
from app.db.database import get_db_session
from app.main import app
from app.models.client import Client
from app.models.user import User


class FakeIntegrityViolation(Exception):
    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class FakeScalarsResult:
    def __init__(self, items: list[Client]) -> None:
        self.items = items

    def all(self) -> list[Client]:
        return self.items


class FakeClientSession:
    def __init__(self) -> None:
        self.clients: list[Client] = []
        self.pending: list[Client] = []
        self.deleted: list[Client] = []
        self.quote_client_ids: set[UUID] = set()

    def add(self, instance: object) -> None:
        assert isinstance(instance, Client)
        self.pending.append(instance)

    async def execute(self, statement: object) -> SimpleNamespace:
        matching = self._matching_clients(statement)
        return SimpleNamespace(scalars=lambda: FakeScalarsResult(matching))

    async def scalars(self, statement: object) -> FakeScalarsResult:
        matching = self._matching_clients(statement)
        matching.sort(key=lambda client: (client.name, client.id))
        offset = getattr(statement, "_offset_clause", None)
        limit = getattr(statement, "_limit_clause", None)
        start = offset.value if offset is not None else 0
        end = start + limit.value if limit is not None else None
        return FakeScalarsResult(matching[start:end])

    async def scalar(self, statement: object) -> Client | None:
        matching = self._matching_clients(statement)
        return matching[0] if matching else None

    def _matching_clients(self, statement: object) -> list[Client]:
        criteria = getattr(statement, "_where_criteria")
        filters = {
            criterion.left.key: criterion.right.value
            for criterion in criteria
        }
        return [
            client
            for client in self.clients
            if all(getattr(client, key) == value for key, value in filters.items())
        ]

    async def commit(self) -> None:
        for client in self.pending:
            duplicate_document = client.document is not None and any(
                existing.document == client.document
                and existing.company_id == client.company_id
                and existing.id != client.id
                for existing in self.clients
            )
            if duplicate_document:
                raise IntegrityError(
                    "INSERT or UPDATE clients",
                    {},
                    FakeIntegrityViolation("uq_clients_company_document"),
                )

        for client in self.deleted:
            if client.id in self.quote_client_ids:
                raise IntegrityError(
                    "DELETE clients",
                    {},
                    FakeIntegrityViolation("fk_quotes_client_id"),
                )
            self.clients.remove(client)

        for client in self.pending:
            client.id = client.id or uuid4()
            client.created_at = client.created_at or datetime.now(timezone.utc)
            client.updated_at = datetime.now(timezone.utc)
            if client not in self.clients:
                self.clients.append(client)

        self.pending.clear()
        self.deleted.clear()

    async def refresh(self, _instance: object) -> None:
        del _instance
        return None

    async def rollback(self) -> None:
        self.pending.clear()
        self.deleted.clear()

    async def delete(self, instance: object) -> None:
        assert isinstance(instance, Client)
        self.deleted.append(instance)


@pytest.fixture
def client_api(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FakeClientSession, User]]:
    session = FakeClientSession()
    company_id = uuid4()
    current_user = User(
        id=uuid4(),
        company_id=company_id,
        name="Owner",
        email="owner@example.com",
        role="owner",
        password_hash="unused",
    )

    async def override_session() -> AsyncIterator[FakeClientSession]:
        yield session

    async def override_user() -> User:
        return current_user

    monkeypatch.setitem(app.dependency_overrides, get_db_session, override_session)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)
    yield session, current_user
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_client_crud_is_scoped_to_current_company(
    client_api: tuple[FakeClientSession, User],
) -> None:
    session, user = client_api
    other_company_client = Client(
        id=uuid4(),
        company_id=uuid4(),
        name="Other tenant",
        phone=None,
        email=None,
        document=None,
        address=None,
    )
    session.clients.append(other_company_client)

    with TestClient(app) as client:
        created = client.post(
            "/clients",
            json={
                "name": "Acme",
                "email": "contact@acme.example",
                "document": "DOC-1",
            },
        )
        assert created.status_code == 201
        created_data = created.json()
        client_id = created_data["id"]
        assert created_data["company_id"] == str(user.company_id)

        listed = client.get("/clients")
        assert listed.status_code == 200
        assert [item["name"] for item in listed.json()] == ["Acme"]

        updated = client.patch(
            f"/clients/{client_id}",
            json={"phone": "+55 11 99999-9999"},
        )
        assert updated.status_code == 200
        assert updated.json()["phone"] == "+55 11 99999-9999"

        fetched = client.get(f"/clients/{client_id}")
        cross_tenant = client.get(f"/clients/{other_company_client.id}")
        assert fetched.status_code == 200
        assert cross_tenant.status_code == 404

        deleted = client.delete(f"/clients/{client_id}")
        missing_after_delete = client.get(f"/clients/{client_id}")

    assert deleted.status_code == 204
    assert missing_after_delete.status_code == 404


@pytest.mark.usefixtures("client_api")
def test_duplicate_document_and_invalid_updates_are_rejected() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/clients",
            json={"name": "First", "document": "DUPLICATE"},
        )
        duplicate = client.post(
            "/clients",
            json={"name": "Second", "document": "DUPLICATE"},
        )
        null_name = client.patch(
            f"/clients/{first.json()['id']}",
            json={"name": None},
        )
        invalid_email = client.post(
            "/clients",
            json={"name": "Bad email", "email": "not-an-email"},
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert null_name.status_code == 422
    assert invalid_email.status_code == 422


def test_client_with_quotes_cannot_be_deleted(
    client_api: tuple[FakeClientSession, User],
) -> None:
    session, _ = client_api
    with TestClient(app) as client:
        created = client.post("/clients", json={"name": "Quoted client"})
        client_id = UUID(created.json()["id"])
        session.quote_client_ids.add(client_id)

        response = client.delete(f"/clients/{client_id}")

    assert response.status_code == 409


def test_client_routes_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/clients")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
