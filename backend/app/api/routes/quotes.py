from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db_session
from app.models.enums import QuoteStatus
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.user import User
from app.services import quote_pdf
from app.schemas.quote import (
    QuoteCreate,
    QuoteItemCreate,
    QuoteItemResponse,
    QuoteItemUpdate,
    QuoteFinancialSummary,
    QuoteResponse,
    QuoteStatusUpdate,
    QuoteUpdate,
)
from app.schemas.quote_delivery import (
    QuoteDeliveryResponse,
    QuoteEmailRequest,
    QuoteWhatsAppRequest,
)
from app.services import quote_delivery, quotes

router = APIRouter(prefix="/quotes")


async def _get_quote_or_404(
    session: AsyncSession,
    company_id: UUID,
    quote_id: UUID,
) -> Quote:
    quote = await quotes.get_quote(session, company_id, quote_id)
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found.",
        )
    return quote


@router.get("", response_model=list[QuoteResponse])
async def list_company_quotes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    quote_status: QuoteStatus | None = Query(default=None, alias="status"),
    client_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Quote]:
    return await quotes.list_quotes(
        session,
        current_user.company_id,
        offset=offset,
        limit=limit,
        status=quote_status,
        client_id=client_id,
    )


@router.get("/summary", response_model=QuoteFinancialSummary)
async def company_quote_financial_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Decimal | int]:
    return await quotes.financial_summary(session, current_user.company_id)


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_quote(
    payload: QuoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    try:
        return await quotes.create_quote(session, current_user.company_id, payload)
    except quotes.QuoteValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{quote_id}", response_model=QuoteResponse)
async def read_company_quote(
    quote_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    return await _get_quote_or_404(session, current_user.company_id, quote_id)


@router.get("/{quote_id}/pdf")
async def download_company_quote_pdf(
    quote_id: UUID,
    download: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    pdf = await run_in_threadpool(quote_pdf.generate_quote_pdf, quote)
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'{disposition}; filename="orcamento-{quote.number:04d}.pdf"'
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/{quote_id}/send/email",
    response_model=QuoteDeliveryResponse,
)
async def email_company_quote(
    quote_id: UUID,
    payload: QuoteEmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QuoteDeliveryResponse:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        await quote_delivery.send_quote_email(
            quote,
            str(payload.recipient) if payload.recipient else None,
            payload.message,
        )
    except quote_delivery.QuoteDeliveryConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except quote_delivery.QuoteDeliveryProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return QuoteDeliveryResponse(detail="Orçamento enviado por email.")


@router.post(
    "/{quote_id}/send/whatsapp",
    response_model=QuoteDeliveryResponse,
)
async def whatsapp_company_quote(
    quote_id: UUID,
    payload: QuoteWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QuoteDeliveryResponse:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        await quote_delivery.send_quote_whatsapp(
            quote,
            payload.recipient_phone,
            payload.message,
        )
    except quote_delivery.QuoteDeliveryConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except quote_delivery.QuoteDeliveryProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return QuoteDeliveryResponse(detail="Orçamento enviado pelo WhatsApp.")


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_company_quote(
    quote_id: UUID,
    payload: QuoteUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        return await quotes.update_quote(session, quote, payload)
    except quotes.QuoteValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/{quote_id}/status", response_model=QuoteResponse)
async def update_quote_status(
    quote_id: UUID,
    payload: QuoteStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        return await quotes.transition_quote(session, quote, payload.status)
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/{quote_id}/cancel", response_model=QuoteResponse)
async def cancel_quote(
    quote_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        return await quotes.transition_quote(
            session,
            quote,
            QuoteStatus.CANCELLED,
        )
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_quote(
    quote_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        await quotes.delete_quote(session, quote)
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{quote_id}/items",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quote_item(
    quote_id: UUID,
    payload: QuoteItemCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Quote:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        return await quotes.add_quote_item(session, quote, payload)
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except quotes.QuoteValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{quote_id}/items/{item_id}",
    response_model=QuoteItemResponse,
)
async def update_quote_item(
    quote_id: UUID,
    item_id: UUID,
    payload: QuoteItemUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QuoteItem:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        updated_quote = await quotes.update_quote_item(
            session,
            quote,
            item_id,
            payload,
        )
    except quotes.QuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote item not found.",
        ) from exc
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return next(item for item in updated_quote.items if item.id == item_id)


@router.delete(
    "/{quote_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quote_item(
    quote_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    quote = await _get_quote_or_404(session, current_user.company_id, quote_id)
    try:
        await quotes.remove_quote_item(session, quote, item_id)
    except quotes.QuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote item not found.",
        ) from exc
    except quotes.QuoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
