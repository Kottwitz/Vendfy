import base64
import zlib
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import get_current_user
from app.db.database import get_db_session
from app.main import app
from app.models.client import Client
from app.models.company import Company
from app.models.enums import QuoteStatus
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.user import User
from app.services import quotes
from app.services.quote_pdf import _format_date, generate_quote_pdf


@pytest.fixture
def quote_pdf_api(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Quote, User]]:
    company_id = uuid4()
    quote_id = uuid4()
    company = Company(
        id=company_id,
        name="Construtora Árvore",
        document="12.345.678/0001-90",
        email="contato@arvore.example",
        phone=None,
        address="São Paulo, SP",
    )
    client = Client(
        id=uuid4(),
        company_id=company_id,
        name="Cliente & Filhos",
        phone="(11) 99999-9999",
        email="cliente@example.com",
        document=None,
        address=None,
    )
    quote = Quote(
        id=quote_id,
        company_id=company_id,
        client_id=client.id,
        number=7,
        status=QuoteStatus.DRAFT,
        subtotal=Decimal("1250.00"),
        discount=Decimal("50.00"),
        total=Decimal("1200.00"),
        description="Reforma da área externa",
        valid_until=None,
        created_at=datetime(2026, 10, 12, 15, 30, tzinfo=timezone.utc),
        company=company,
        client=client,
        items=[
            QuoteItem(
                id=uuid4(),
                quote_id=quote_id,
                description="Mão de obra e materiais",
                quantity=Decimal("2.000"),
                unit_price=Decimal("625.00"),
                total=Decimal("1250.00"),
            )
        ],
    )
    user = User(
        id=uuid4(),
        company_id=company_id,
        name="Owner",
        email="owner@example.com",
        role="owner",
        password_hash="unused",
    )

    async def get_quote(
        _session: object,
        requested_company_id: object,
        requested_quote_id: object,
    ) -> Quote | None:
        del _session
        if (
            requested_company_id == company_id
            and requested_quote_id == quote_id
        ):
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


def _extract_pdf_content(pdf: bytes) -> bytes:
    stream_start = pdf.index(b"stream\n") + len(b"stream\n")
    stream_end = pdf.index(b"endstream", stream_start)
    encoded_stream = pdf[stream_start:stream_end].strip()
    return zlib.decompress(base64.a85decode(encoded_stream, adobe=True))


def test_generate_quote_pdf_returns_a_complete_pdf(
    quote_pdf_api: tuple[Quote, User],
) -> None:
    quote, _ = quote_pdf_api
    quote.valid_until = date(2026, 10, 30)
    pdf = generate_quote_pdf(quote)

    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    content = _extract_pdf_content(pdf)
    assert b"12 de outubro de 2026" in content
    assert b"30 de outubro de 2026" in content
    assert b"PRAZO DE VALIDADE" in content


def test_quote_pdf_explains_when_validity_date_is_not_set(
    quote_pdf_api: tuple[Quote, User],
) -> None:
    quote, _ = quote_pdf_api
    assert _format_date(quote.valid_until) == "Não informada"
    assert b"informada" in _extract_pdf_content(generate_quote_pdf(quote))
    assert _format_date(
        datetime(2026, 10, 12, 2, 30, tzinfo=timezone.utc)
    ) == "11 de outubro de 2026"


def test_quote_pdf_download_and_preview_are_scoped_to_company(
    quote_pdf_api: tuple[Quote, User],
) -> None:
    quote, _ = quote_pdf_api
    with TestClient(app) as client:
        download = client.get(f"/quotes/{quote.id}/pdf")
        preview = client.get(f"/quotes/{quote.id}/pdf?download=false")
        cross_tenant = client.get(f"/quotes/{uuid4()}/pdf")

    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"] == (
        'attachment; filename="orcamento-0007.pdf"'
    )
    assert download.content.startswith(b"%PDF-")
    assert preview.status_code == 200
    assert preview.headers["content-disposition"].startswith("inline;")
    assert cross_tenant.status_code == 404
