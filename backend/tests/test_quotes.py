import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import QuoteStatus
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.schemas.quote import QuoteCreate, QuoteItemCreate, QuoteItemUpdate
from app.services import quotes


def make_quote(
    status: QuoteStatus = QuoteStatus.DRAFT,
    *,
    discount: Decimal = Decimal("0.00"),
    items: list[QuoteItem] | None = None,
) -> Quote:
    return Quote(
        id=uuid4(),
        company_id=uuid4(),
        client_id=uuid4(),
        number=1,
        status=status,
        subtotal=Decimal("0.00"),
        discount=discount,
        total=Decimal("0.00"),
        description=None,
        valid_until=None,
        items=items or [],
    )


def test_line_and_quote_totals_are_calculated_with_money_rounding() -> None:
    line = QuoteItem(
        description="Labor",
        quantity=Decimal("0.333"),
        unit_price=Decimal("0.05"),
        total=Decimal("0"),
    )
    quote = make_quote(
        discount=Decimal("0.01"),
        items=[
            line,
            QuoteItem(
                description="Materials",
                quantity=Decimal("2.000"),
                unit_price=Decimal("1.23"),
                total=Decimal("0"),
            ),
        ],
    )
    for item in quote.items:
        item.total = quotes._item_total(item)

    quotes._recalculate_totals(quote)

    assert line.total == Decimal("0.02")
    assert quote.subtotal == Decimal("2.48")
    assert quote.total == Decimal("2.47")


def test_discount_above_subtotal_is_rejected() -> None:
    quote = make_quote(
        discount=Decimal("1.00"),
        items=[
            QuoteItem(
                description="Service",
                quantity=Decimal("1.000"),
                unit_price=Decimal("0.50"),
                total=Decimal("0.50"),
            )
        ],
    )

    with pytest.raises(
        quotes.QuoteValidationError,
        match="Discount cannot exceed",
    ):
        quotes._recalculate_totals(quote)


def test_item_total_cannot_exceed_database_precision() -> None:
    item = QuoteItem(
        description="Oversized",
        quantity=Decimal("999999999.999"),
        unit_price=Decimal("999999999999.99"),
        total=Decimal("0"),
    )

    with pytest.raises(
        quotes.QuoteValidationError,
        match="item total exceeds",
    ):
        quotes._item_total(item)


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (QuoteStatus.DRAFT, QuoteStatus.SENT, True),
        (QuoteStatus.DRAFT, QuoteStatus.CANCELLED, True),
        (QuoteStatus.SENT, QuoteStatus.VIEWED, True),
        (QuoteStatus.SENT, QuoteStatus.APPROVED, True),
        (QuoteStatus.SENT, QuoteStatus.REJECTED, True),
        (QuoteStatus.VIEWED, QuoteStatus.CANCELLED, True),
        (QuoteStatus.APPROVED, QuoteStatus.CANCELLED, False),
        (QuoteStatus.CANCELLED, QuoteStatus.SENT, False),
        (QuoteStatus.EXPIRED, QuoteStatus.APPROVED, False),
    ],
)
def test_quote_status_transition_rules(
    current: QuoteStatus,
    target: QuoteStatus,
    allowed: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_test() -> None:
        quote = make_quote(current)
        commit_mock = AsyncMock()
        session = cast(AsyncSession, SimpleNamespace(commit=commit_mock))
        monkeypatch.setattr(quotes, "get_quote", AsyncMock(return_value=quote))

        if allowed:
            updated = await quotes.transition_quote(session, quote, target)
            assert updated.status is target
            commit_mock.assert_awaited_once()
        else:
            with pytest.raises(quotes.QuoteConflictError):
                await quotes.transition_quote(session, quote, target)
            commit_mock.assert_not_awaited()

    asyncio.run(run_test())


def test_create_quote_rejects_client_from_another_company() -> None:
    async def run_test() -> None:
        scalar_mock = AsyncMock(return_value=None)
        session = cast(AsyncSession, SimpleNamespace(scalar=scalar_mock))
        payload = QuoteCreate(client_id=uuid4(), items=[])

        with pytest.raises(
            quotes.QuoteValidationError,
            match="Client not found in this company",
        ):
            await quotes.create_quote(session, uuid4(), payload)

        scalar_mock.assert_awaited_once()

    asyncio.run(run_test())


def test_financial_summary_uses_approved_revenue_and_recorded_costs() -> None:
    async def run_test() -> None:
        session = cast(
            AsyncSession,
            SimpleNamespace(
                execute=AsyncMock(
                    return_value=SimpleNamespace(
                        one=lambda: SimpleNamespace(
                            gross_revenue=Decimal("1200.00"),
                            expenses=Decimal("450.00"),
                            missing_cost_items=2,
                        )
                    )
                )
            ),
        )

        summary = await quotes.financial_summary(session, uuid4())

        assert summary == {
            "gross_revenue": Decimal("1200.00"),
            "expenses": Decimal("450.00"),
            "profit": Decimal("750.00"),
            "missing_cost_items": 2,
        }
        session.execute.assert_awaited_once()

    asyncio.run(run_test())


def test_any_quote_status_can_be_deleted() -> None:
    async def run_test() -> None:
        quote = make_quote(QuoteStatus.APPROVED)
        delete_mock = AsyncMock()
        commit_mock = AsyncMock()
        session = cast(
            AsyncSession,
            SimpleNamespace(delete=delete_mock, commit=commit_mock),
        )

        await quotes.delete_quote(session, quote)

        delete_mock.assert_awaited_once_with(quote)
        commit_mock.assert_awaited_once()

    asyncio.run(run_test())


def test_approved_quote_item_cost_can_be_recorded_but_price_is_locked() -> None:
    async def run_test() -> None:
        item = QuoteItem(
            id=uuid4(),
            quote_id=uuid4(),
            description="Approved service",
            quantity=Decimal("2.000"),
            unit_price=Decimal("100.00"),
            unit_cost=None,
            total=Decimal("200.00"),
        )
        quote = make_quote(QuoteStatus.APPROVED, items=[item])
        session = cast(AsyncSession, SimpleNamespace(commit=AsyncMock()))
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(quotes, "get_quote", AsyncMock(return_value=quote))
        try:
            await quotes.update_quote_item(
                session,
                quote,
                item.id,
                QuoteItemUpdate(unit_cost=Decimal("35.00")),
            )
            assert item.unit_cost == Decimal("35.00")
            with pytest.raises(quotes.QuoteConflictError, match="Only item costs"):
                await quotes.update_quote_item(
                    session,
                    quote,
                    item.id,
                    QuoteItemUpdate(unit_price=Decimal("90.00")),
                )
        finally:
            monkeypatch.undo()

    asyncio.run(run_test())


def test_quote_schema_rejects_invalid_item_amounts() -> None:
    with pytest.raises(ValueError):
        QuoteItemCreate(
            description="Invalid quantity",
            quantity=Decimal("0"),
            unit_price=Decimal("1.00"),
        )
    with pytest.raises(ValueError):
        QuoteItemCreate(
            description="Invalid price",
            quantity=Decimal("1.000"),
            unit_price=Decimal("-0.01"),
        )
    with pytest.raises(ValueError):
        QuoteItemCreate(
            description="Invalid cost",
            quantity=Decimal("1.000"),
            unit_price=Decimal("1.00"),
            unit_cost=Decimal("-0.01"),
        )
