from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db_session
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyResponse, CompanyUpdate
from app.services.credentials import CredentialEncryptionError, encrypt_credential

router = APIRouter(prefix="/companies")


def _response(company: Company) -> CompanyResponse:
    if company.smtp_security == "starttls":
        smtp_security: Literal["starttls", "ssl"] = "starttls"
    elif company.smtp_security == "ssl":
        smtp_security = "ssl"
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Company has an unsupported SMTP security mode.",
        )
    return CompanyResponse(
        id=company.id,
        name=company.name,
        document=company.document,
        phone=company.phone,
        email=company.email,
        address=company.address,
        whatsapp_phone_number_id=company.whatsapp_phone_number_id,
        whatsapp_configured=bool(
            company.whatsapp_phone_number_id
            and company.whatsapp_access_token_encrypted
        ),
        smtp_host=company.smtp_host,
        smtp_port=company.smtp_port,
        smtp_username=company.smtp_username,
        smtp_security=smtp_security,
        smtp_configured=bool(
            company.smtp_host
            and company.smtp_port
            and company.smtp_username
            and company.smtp_password_encrypted
            and company.email
        ),
    )


async def _get_company(session: AsyncSession, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )
    return company


@router.get("/me", response_model=CompanyResponse)
async def read_company_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyResponse:
    company = await _get_company(session, current_user.company_id)
    return _response(company)


@router.patch("/me", response_model=CompanyResponse)
async def update_company_settings(
    payload: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyResponse:
    company = await _get_company(session, current_user.company_id)
    changes = payload.model_dump(
        exclude={
            "whatsapp_access_token",
            "clear_whatsapp_access_token",
            "smtp_password",
            "clear_smtp_password",
        }
    )
    for field, value in changes.items():
        setattr(company, field, value)

    if payload.clear_whatsapp_access_token:
        company.whatsapp_access_token_encrypted = None
    elif payload.whatsapp_access_token:
        try:
            company.whatsapp_access_token_encrypted = encrypt_credential(
                payload.whatsapp_access_token
            )
        except CredentialEncryptionError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    if payload.clear_smtp_password:
        company.smtp_password_encrypted = None
    elif payload.smtp_password:
        try:
            company.smtp_password_encrypted = encrypt_credential(
                payload.smtp_password
            )
        except CredentialEncryptionError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    session.add(company)
    await session.commit()
    await session.refresh(company)
    return _response(company)
