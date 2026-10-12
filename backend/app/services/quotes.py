from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.company import Company
from app.models.enums import QuoteStatus
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.schemas.quote import QuoteCreate, QuoteItemCreate, QuoteItemUpdate, QuoteUpdate

CENT = Decimal("0.01")
MAX_MONEY = Decimal("999999999999.99")
ALLOWED_TRANSITIONS: dict[QuoteStatus, set[QuoteStatus]] = {
    QuoteStatus.DRAFT: {QuoteStatus.SENT, QuoteStatus.CANCELLED},
    QuoteStatus.SENT: {
        QuoteStatus.VIEWED,
        QuoteStatus.APPROVED,
        QuoteStatus.REJECTED,
        QuoteStatus.CANCELLED,
    },
    QuoteStatus.VIEWED: {
        QuoteStatus.APPROVED,
        QuoteStatus.REJECTED,
        QuoteStatus.CANCELLED,
    },
    QuoteStatus.APPROVED: set(),
    QuoteStatus.REJECTED: set(),
    QuoteStatus.EXPIRED: set(),
    QuoteStatus.CANCELLED: set(),
}


class QuoteNotFoundError(Exception):
    pass


class QuoteConflictError(Exception):
    pass


class QuoteValidationError(Exception):
    pass


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _item_total(item: QuoteItemCreate | QuoteItem) -> Decimal:
    total = _money(item.quantity * item.unit_price)
    if total > MAX_MONEY:
        raise QuoteValidationError("Quote item total exceeds the supported limit.")
    return total


def _recalculate_totals(quote: Quote) -> None:
    subtotal = sum((item.total for item in quote.items), Decimal("0.00"))
    discount = _money(quote.discount)
    if subtotal > MAX_MONEY:
        raise QuoteValidationError("Quote subtotal exceeds the supported limit.")
    if discount > subtotal:
        raise QuoteValidationError("Discount cannot exceed the quote subtotal.")
    quote.subtotal = _money(subtotal)
    quote.discount = discount
    quote.total = _money(subtotal - discount)


async def _validate_client(
    session: AsyncSession,
    company_id: UUID,
    client_id: UUID,
) -> None:
    client = await session.scalar(
        select(Client.id).where(
            Client.id == client_id,
            Client.company_id == company_id,
        )
    )
    if client is None:
        raise QuoteValidationError("Client not found in this company.")


async def list_quotes(
    session: AsyncSession,
    company_id: UUID,
    *,
    offset: int = 0,
    limit: int = 100,
    status: QuoteStatus | None = None,
    client_id: UUID | None = None,
) -> list[Quote]:
    statement = (
        select(Quote)
        .options(selectinload(Quote.items))
        .where(Quote.company_id == company_id)
    )
    if status is not None:
        statement = statement.where(Quote.status == status)
    if client_id is not None:
        statement = statement.where(Quote.client_id == client_id)
    statement = (
        statement.order_by(Quote.number.desc(), Quote.id)
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(statement)
    return list(result.all())


async def financial_summary(
    session: AsyncSession,
    company_id: UUID,
) -> dict[str, Decimal | int]:
    gross_revenue_query = (
        select(func.coalesce(func.sum(Quote.total), 0)).where(
            Quote.company_id == company_id,
            Quote.status == QuoteStatus.APPROVED,
        )
    )
    expenses_query = (
        select(
            func.coalesce(func.sum(QuoteItem.quantity * QuoteItem.unit_cost), 0)
        )
        .join(Quote, Quote.id == QuoteItem.quote_id)
        .where(
            Quote.company_id == company_id,
            Quote.status == QuoteStatus.APPROVED,
            QuoteItem.unit_cost.is_not(None),
        )
    )
    missing_costs_query = (
        select(func.count(QuoteItem.id))
        .join(Quote, Quote.id == QuoteItem.quote_id)
        .where(
            Quote.company_id == company_id,
            Quote.status == QuoteStatus.APPROVED,
            QuoteItem.unit_cost.is_(None),
        )
    )
    result = await session.execute(
        select(
            gross_revenue_query.scalar_subquery().label("gross_revenue"),
            expenses_query.scalar_subquery().label("expenses"),
            missing_costs_query.scalar_subquery().label("missing_cost_items"),
        )
    )
    summary = result.one()
    revenue_amount = summary.gross_revenue or Decimal("0.00")
    expenses_amount = summary.expenses or Decimal("0.00")
    return {
        "gross_revenue": revenue_amount,
        "expenses": expenses_amount,
        "profit": revenue_amount - expenses_amount,
        "missing_cost_items": summary.missing_cost_items or 0,
    }


async def get_quote(
    session: AsyncSession,
    company_id: UUID,
    quote_id: UUID,
) -> Quote | None:
    statement = (
        select(Quote)
        .options(
            selectinload(Quote.items),
            selectinload(Quote.client),
            selectinload(Quote.company),
        )
        .where(Quote.company_id == company_id, Quote.id == quote_id)
    )
    return await session.scalar(statement)


def _add_items(quote: Quote, items: list[QuoteItemCreate]) -> None:
    quote.items = [
        QuoteItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            unit_cost=item.unit_cost,
            total=_item_total(item),
        )
        for item in items
    ]


async def create_quote(
    session: AsyncSession,
    company_id: UUID,
    payload: QuoteCreate,
) -> Quote:
    await _validate_client(session, company_id, payload.client_id)
    company_result = await session.scalar(
        select(Company.id).where(Company.id == company_id).with_for_update()
    )
    if company_result is None:
        raise QuoteValidationError("Company not found.")

    latest_number = await session.scalar(
        select(func.max(Quote.number)).where(Quote.company_id == company_id)
    )
    quote = Quote(
        company_id=company_id,
        client_id=payload.client_id,
        number=(latest_number or 0) + 1,
        status=QuoteStatus.DRAFT,
        discount=payload.discount,
        description=payload.description,
        valid_until=payload.valid_until,
        items=[],
    )
    _add_items(quote, payload.items)
    _recalculate_totals(quote)
    session.add(quote)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return await get_quote(session, company_id, quote.id) or quote


async def update_quote(
    session: AsyncSession,
    quote: Quote,
    payload: QuoteUpdate,
) -> Quote:
    if quote.status is not QuoteStatus.DRAFT:
        raise QuoteConflictError("Only draft quotes can be edited.")
    changes = payload.model_dump(exclude_unset=True)
    new_client_id = changes.pop("client_id", None)
    if new_client_id is not None:
        await _validate_client(session, quote.company_id, new_client_id)
        quote.client_id = new_client_id
    items = changes.pop("items", None)
    for field, value in changes.items():
        setattr(quote, field, value)
    if items is not None:
        _add_items(quote, items)
    try:
        _recalculate_totals(quote)
        await session.commit()
    except (QuoteValidationError, IntegrityError):
        await session.rollback()
        raise
    return await get_quote(session, quote.company_id, quote.id) or quote


async def add_quote_item(
    session: AsyncSession,
    quote: Quote,
    payload: QuoteItemCreate,
) -> Quote:
    _ensure_editable(quote)
    item = QuoteItem(
        description=payload.description,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        unit_cost=payload.unit_cost,
        total=_item_total(payload),
    )
    quote.items.append(item)
    await _commit_recalculated(session, quote)
    return await get_quote(session, quote.company_id, quote.id) or quote


async def update_quote_item(
    session: AsyncSession,
    quote: Quote,
    item_id: UUID,
    payload: QuoteItemUpdate,
) -> Quote:
    item = next((entry for entry in quote.items if entry.id == item_id), None)
    if item is None:
        raise QuoteNotFoundError
    changes = payload.model_dump(exclude_unset=True)
    if quote.status is not QuoteStatus.DRAFT and set(changes) != {"unit_cost"}:
        raise QuoteConflictError(
            "Only item costs can be changed after a quote leaves draft status."
        )
    for field, value in changes.items():
        setattr(item, field, value)
    item.total = _item_total(item)
    await _commit_recalculated(session, quote)
    return await get_quote(session, quote.company_id, quote.id) or quote


async def remove_quote_item(
    session: AsyncSession,
    quote: Quote,
    item_id: UUID,
) -> Quote:
    _ensure_editable(quote)
    item = next((entry for entry in quote.items if entry.id == item_id), None)
    if item is None:
        raise QuoteNotFoundError
    quote.items.remove(item)
    await _commit_recalculated(session, quote)
    return await get_quote(session, quote.company_id, quote.id) or quote


async def transition_quote(
    session: AsyncSession,
    quote: Quote,
    new_status: QuoteStatus,
) -> Quote:
    if new_status not in ALLOWED_TRANSITIONS[quote.status]:
        raise QuoteConflictError(
            f"Cannot transition quote from {quote.status.value} to {new_status.value}."
        )
    quote.status = new_status
    await session.commit()
    return await get_quote(session, quote.company_id, quote.id) or quote


async def delete_quote(session: AsyncSession, quote: Quote) -> None:
    await session.delete(quote)
    await session.commit()


def _ensure_editable(quote: Quote) -> None:
    if quote.status is not QuoteStatus.DRAFT:
        raise QuoteConflictError("Items can only be changed on draft quotes.")


async def _commit_recalculated(session: AsyncSession, quote: Quote) -> None:
    try:
        _recalculate_totals(quote)
        await session.commit()
    except (QuoteValidationError, IntegrityError):
        await session.rollback()
        raise
