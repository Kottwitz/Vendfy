from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.user import User as UserModel
from app.schemas.auth import TokenData

_password_hasher = PasswordHasher()


class DuplicateEmailError(Exception):
    pass


def _get_jwt_secret() -> str:
    secret = settings.security.jwt_secret_key
    if secret is None:
        raise RuntimeError(
            "SECURITY__JWT_SECRET_KEY must be configured before using JWT authentication."
        )
    return secret.get_secret_value()


def get_password_hash(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(
    data: Mapping[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    subject = data.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("JWT data must include a non-empty string 'sub' claim.")

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.security.access_token_expire_minutes)
    )
    claims = dict(data)
    claims.update({"iat": now, "exp": expires_at})
    return jwt.encode(
        claims,
        _get_jwt_secret(),
        algorithm=settings.security.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenData:
    payload = jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=[settings.security.jwt_algorithm],
        options={"require_sub": True, "require_exp": True},
    )
    try:
        return TokenData.model_validate(payload)
    except ValidationError as exc:
        raise JWTError("Token is missing valid required claims.") from exc


async def register_company_and_user(
    *,
    email: str,
    password: str,
    session: AsyncSession,
    name: str | None = None,
    company_name: str | None = None,
    company_email: str | None = None,
    company_phone: str | None = None,
) -> UserModel:
    normalized_email = email.strip().lower()
    email_name = normalized_email.partition("@")[0]
    user = UserModel(
        email=normalized_email,
        name=name or email_name,
        role="owner",
        password_hash=get_password_hash(password),
        email_verified=True,
        company=Company(
            name=company_name or email_name,
            email=company_email.strip().lower() if company_email else None,
            phone=company_phone,
        ),
    )
    session.add(user.company)
    session.add(user)

    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError as exc:
        await session.rollback()
        original_error = getattr(exc, "orig", None)
        constraint_name = getattr(original_error, "constraint_name", None)
        if constraint_name == "uq_users_email":
            raise DuplicateEmailError from exc
        raise

    return user


async def authenticate_user(
    email: str,
    password: str,
    session: AsyncSession,
) -> UserModel | None:
    statement = select(UserModel).where(UserModel.email == email.strip().lower())
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
