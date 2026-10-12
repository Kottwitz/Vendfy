import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from decimal import Decimal
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.routes.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db_session
from app.main import app
from app.models.client import Client
from app.models.company import Company
from app.models.enums import QuoteStatus
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.user import User
from app.services import quote_delivery, quotes
from app.services.credentials import encrypt_credential
from app.services.quote_delivery import QuoteDeliveryConfigurationError


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings.security,
        "credential_encryption_key",
        SecretStr(Fernet.generate_key().decode("ascii")),
    )


def make_quote() -> Quote:
    company_id = uuid4()
    client = Client(
        id=uuid4(),
        company_id=company_id,
        name="Cliente Exemplo",
        phone="+55 11 99999-9999",
        email="cliente@example.com",
        document=None,
        address=None,
    )
    company = Company(
        id=company_id,
        name="Construtora Vendfy",
        document=None,
        phone="+55 11 3333-4444",
        email="comercial@example.com",
        logo=None,
        address=None,
        whatsapp_phone_number_id="123456789",
        whatsapp_access_token_encrypted=encrypt_credential("whatsapp-secret"),
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="comercial@example.com",
        smtp_password_encrypted=encrypt_credential("smtp-secret"),
        smtp_security="starttls",
    )
    quote_id = uuid4()
    return Quote(
        id=quote_id,
        company_id=company_id,
        client_id=client.id,
        number=14,
        status=QuoteStatus.DRAFT,
        subtotal=Decimal("500.00"),
        discount=Decimal("0.00"),
        total=Decimal("500.00"),
        description="Instalação elétrica",
        valid_until=None,
        created_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
        company=company,
        client=client,
        items=[
            QuoteItem(
                id=uuid4(),
                quote_id=quote_id,
                description="Serviço",
                quantity=Decimal("1.000"),
                unit_price=Decimal("500.00"),
                total=Decimal("500.00"),
            )
        ],
    )


def test_quote_email_attaches_pdf_and_uses_company_sender(monkeypatch) -> None:
    quote = make_quote()
    sent: list[
        tuple[quote_delivery.SMTPConfiguration, EmailMessage, str]
    ] = []

    def capture_send(
        smtp: quote_delivery.SMTPConfiguration,
        email: EmailMessage,
        password: str,
    ) -> None:
        sent.append((smtp, email, password))

    monkeypatch.setattr(
        quote_delivery,
        "_send_smtp_message",
        capture_send,
    )

    asyncio.run(
        quote_delivery.send_quote_email(
            quote,
            "custom@example.com",
            "Segue nossa proposta.",
        )
    )

    smtp, email, password = sent[0]
    assert smtp.host == "smtp.example.com"
    assert smtp.username == "comercial@example.com"
    assert smtp.security == "starttls"
    assert str(email["From"]).endswith("<comercial@example.com>")
    assert email["To"] == "custom@example.com"
    attachment = list(email.iter_attachments())[0]
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_filename() == "orcamento-0014.pdf"
    pdf = attachment.get_payload(decode=True)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert password == "smtp-secret"


def test_quote_whatsapp_uploads_pdf_and_sends_document(monkeypatch) -> None:
    quote = make_quote()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "media-123"})
        return httpx.Response(200, json={"messages": [{"id": "sent-123"}]})

    real_async_client = httpx.AsyncClient

    def mock_async_client(*, timeout: float) -> httpx.AsyncClient:
        return real_async_client(
            timeout=timeout,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(quote_delivery.httpx, "AsyncClient", mock_async_client)

    asyncio.run(
        quote_delivery.send_quote_whatsapp(
            quote,
            None,
            "Segue o orçamento.",
        )
    )

    assert len(requests) == 2
    assert requests[0].url.path.endswith("/123456789/media")
    assert requests[0].headers["authorization"] == "Bearer whatsapp-secret"
    assert b"application/pdf" in requests[0].read()
    assert requests[1].url.path.endswith("/123456789/messages")
    message_payload = requests[1].read().decode()
    assert '"to":"5511999999999"' in message_payload
    assert "media-123" in message_payload


def test_invalid_whatsapp_recipient_is_rejected() -> None:
    with pytest.raises(
        QuoteDeliveryConfigurationError,
        match="código do país",
    ):
        quote_delivery._normalize_phone("+123")
    with pytest.raises(
        QuoteDeliveryConfigurationError,
        match="formato internacional",
    ):
        quote_delivery._normalize_phone("11999999999")


def test_smtp_destination_rejects_private_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def resolve_private_address(
        hostname: str,
        port: int,
        *,
        type: int,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert hostname == "mail.example.com"
        assert port == 587
        assert type == quote_delivery.socket.SOCK_STREAM
        return [(2, 1, 6, "", ("127.0.0.1", port))]

    monkeypatch.setattr(
        quote_delivery.socket,
        "getaddrinfo",
        resolve_private_address,
    )

    with pytest.raises(OSError, match="public IP"):
        quote_delivery._connect_public_smtp("mail.example.com", 587, 1)


@pytest.fixture
def quote_delivery_api(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Quote, User]]:
    quote = make_quote()
    user = User(
        id=uuid4(),
        company_id=quote.company_id,
        name="Owner",
        email="owner@example.com",
        role="owner",
        password_hash="unused",
    )

    async def get_quote(
        _session: object,
        company_id: object,
        quote_id: object,
    ) -> Quote | None:
        del _session
        if company_id == user.company_id and quote_id == quote.id:
            return quote
        return None

    async def override_session() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def override_user() -> User:
        return user

    monkeypatch.setattr(quotes, "get_quote", get_quote)
    monkeypatch.setitem(app.dependency_overrides, get_db_session, override_session)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)
    yield quote, user
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_send_quote_routes_are_tenant_scoped(
    quote_delivery_api: tuple[Quote, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quote, _ = quote_delivery_api
    email_mock = AsyncMock()
    whatsapp_mock = AsyncMock()
    monkeypatch.setattr(quote_delivery, "send_quote_email", email_mock)
    monkeypatch.setattr(quote_delivery, "send_quote_whatsapp", whatsapp_mock)
    with TestClient(app) as client:
        email_response = client.post(
            f"/quotes/{quote.id}/send/email",
            json={"recipient": "override@example.com", "message": "Proposta"},
        )
        whatsapp_response = client.post(
            f"/quotes/{quote.id}/send/whatsapp",
            json={"recipient_phone": "+55 (11) 98888-7777"},
        )
        cross_tenant = client.post(
            f"/quotes/{uuid4()}/send/email",
            json={"recipient": "override@example.com"},
        )

    assert email_response.status_code == 200
    assert whatsapp_response.status_code == 200
    assert cross_tenant.status_code == 404
    email_mock.assert_awaited_once_with(
        quote, "override@example.com", "Proposta"
    )
    whatsapp_mock.assert_awaited_once_with(
        quote, "+55 (11) 98888-7777", None
    )
