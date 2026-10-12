from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db_session
from app.models.user import User as UserModel
from app.schemas.auth import (
    MessageResponse,
    RegisterRequest,
    Token,
    User,
)
from app.services import auth

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    normalized_email = str(payload.email).strip().lower()
    try:
        await auth.register_company_and_user(
            email=normalized_email,
            password=payload.password,
            name=payload.name,
            company_name=payload.company_name,
            company_email=str(payload.company_email) if payload.company_email else None,
            company_phone=payload.company_phone,
            session=session,
        )
    except auth.DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return MessageResponse(
        message="Conta criada com sucesso. Agora você pode entrar."
    )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    user = await auth.authenticate_user(
        form_data.username,
        form_data.password,
        session,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(
            minutes=settings.security.access_token_expire_minutes
        ),
    )
    return Token(access_token=access_token)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = auth.decode_access_token(token)
        user_id = UUID(token_data.sub)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc

    user = await session.get(UserModel, user_id)
    if user is None:
        raise credentials_exception
    return user


@router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    return current_user
