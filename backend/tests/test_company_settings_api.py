from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.routes.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db_session
from app.main import app
from app.models.company import Company
from app.models.user import User
from app.services.credentials import decrypt_credential, encrypt_credential


class FakeCompanySession:
    def __init__(self, company: Company) -> None:
        self.company = company

    async def get(self, model: type[Company], company_id: object) -> Company | None:
        assert model is Company
        return self.company if company_id == self.company.id else None

    def add(self, instance: object) -> None:
        assert instance is self.company

    async def commit(self) -> None:
        return None

    async def refresh(self, instance: object) -> None:
        assert instance is self.company


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Construtora Vendfy",
        document=None,
        phone=None,
        email="comercial@example.com",
        logo=None,
        address=None,
        whatsapp_phone_number_id=None,
        whatsapp_access_token_encrypted=None,
        smtp_host=None,
        smtp_port=None,
        smtp_username=None,
        smtp_password_encrypted=None,
        smtp_security="starttls",
    )


def override_company_api(
    monkeypatch: pytest.MonkeyPatch,
    company: Company,
) -> tuple[FakeCompanySession, User]:
    session = FakeCompanySession(company)
    user = User(
        id=uuid4(),
        company_id=company.id,
        name="Owner",
        email="owner@example.com",
        role="owner",
        password_hash="unused",
    )

    async def override_session() -> AsyncIterator[FakeCompanySession]:
        yield session

    async def override_user() -> User:
        return user

    monkeypatch.setitem(app.dependency_overrides, get_db_session, override_session)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)
    return session, user


def clear_company_api_overrides() -> None:
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_company_settings_encrypt_credentials_and_never_return_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = make_company()
    override_company_api(monkeypatch, company)
    monkeypatch.setattr(
        settings.security,
        "credential_encryption_key",
        SecretStr(Fernet.generate_key().decode("ascii")),
    )

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/companies/me",
                json={
                    "name": company.name,
                    "email": company.email,
                    "phone": "+55 11 3333-4444",
                    "whatsapp_phone_number_id": "123456789",
                    "whatsapp_access_token": "meta-access-token",
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_username": "sender@example.com",
                    "smtp_password": "smtp-secret",
                    "smtp_security": "starttls",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["whatsapp_configured"] is True
        assert data["smtp_configured"] is True
        assert "whatsapp_access_token" not in data
        assert "smtp_password" not in data
        assert "meta-access-token" not in response.text
        assert "smtp-secret" not in response.text
        assert company.whatsapp_access_token_encrypted != "meta-access-token"
        assert company.smtp_password_encrypted != "smtp-secret"
        assert company.whatsapp_access_token_encrypted is not None
        assert company.smtp_password_encrypted is not None
        assert (
            decrypt_credential(company.whatsapp_access_token_encrypted)
            == "meta-access-token"
        )
        assert decrypt_credential(company.smtp_password_encrypted) == "smtp-secret"
    finally:
        clear_company_api_overrides()


def test_company_settings_do_not_replace_saved_secret_when_input_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = make_company()
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(
        settings.security,
        "credential_encryption_key",
        SecretStr(key),
    )
    company.whatsapp_phone_number_id = "123456789"
    company.whatsapp_access_token_encrypted = encrypt_credential("existing-token")
    existing_encrypted = company.whatsapp_access_token_encrypted
    override_company_api(monkeypatch, company)

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/companies/me",
                json={
                    "name": company.name,
                    "email": company.email,
                    "whatsapp_phone_number_id": "123456789",
                    "whatsapp_access_token": "",
                    "smtp_security": "starttls",
                },
            )
        assert response.status_code == 200
        assert company.whatsapp_access_token_encrypted == existing_encrypted
        assert response.json()["whatsapp_configured"] is True
    finally:
        clear_company_api_overrides()


def test_company_settings_reject_non_numeric_whatsapp_number_id() -> None:
    from pydantic import ValidationError

    from app.schemas.company import CompanyUpdate

    with pytest.raises(ValidationError):
        CompanyUpdate(
            name="Company",
            whatsapp_phone_number_id="not-an-id",
        )
