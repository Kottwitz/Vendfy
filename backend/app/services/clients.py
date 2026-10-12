from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


class ClientConflictError(Exception):
    pass


def _integrity_constraint_name(error: IntegrityError) -> str | None:
    original_error = getattr(error, "orig", None)
    return getattr(original_error, "constraint_name", None)


async def list_clients(
    session: AsyncSession,
    company_id: UUID,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Client]:
    statement = (
        select(Client)
        .where(Client.company_id == company_id)
        .order_by(Client.name, Client.id)
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(statement)
    return list(result.all())


async def get_client(
    session: AsyncSession,
    company_id: UUID,
    client_id: UUID,
) -> Client | None:
    statement = select(Client).where(
        Client.company_id == company_id,
        Client.id == client_id,
    )
    return await session.scalar(statement)


async def create_client(
    session: AsyncSession,
    company_id: UUID,
    payload: ClientCreate,
) -> Client:
    client = Client(company_id=company_id, **payload.model_dump())
    session.add(client)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if _integrity_constraint_name(exc) == "uq_clients_company_document":
            raise ClientConflictError from exc
        raise
    await session.refresh(client)
    return client


async def update_client(
    session: AsyncSession,
    client: Client,
    payload: ClientUpdate,
) -> Client:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if _integrity_constraint_name(exc) == "uq_clients_company_document":
            raise ClientConflictError from exc
        raise
    await session.refresh(client)
    return client


async def delete_client(session: AsyncSession, client: Client) -> None:
    await session.delete(client)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if _integrity_constraint_name(exc) == "fk_quotes_client_id":
            raise ClientConflictError from exc
        raise
