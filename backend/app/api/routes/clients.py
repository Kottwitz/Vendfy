from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db_session
from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.services import clients

router = APIRouter(prefix="/clients")


@router.get("", response_model=list[ClientResponse])
async def list_company_clients(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Client]:
    return await clients.list_clients(
        session,
        current_user.company_id,
        offset=offset,
        limit=limit,
    )


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_client(
    payload: ClientCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    try:
        return await clients.create_client(session, current_user.company_id, payload)
    except clients.ClientConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this document already exists in the company.",
        ) from exc


@router.get("/{client_id}", response_model=ClientResponse)
async def read_company_client(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    client = await clients.get_client(session, current_user.company_id, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_company_client(
    client_id: UUID,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    client = await clients.get_client(session, current_user.company_id, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )
    try:
        return await clients.update_client(session, client, payload)
    except clients.ClientConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this document already exists in the company.",
        ) from exc


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_client(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    client = await clients.get_client(session, current_user.company_id, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )
    try:
        await clients.delete_client(session, client)
    except clients.ClientConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client cannot be deleted because it has associated quotes.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
