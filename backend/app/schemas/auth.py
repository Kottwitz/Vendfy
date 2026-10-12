from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_email: EmailStr | None = None
    company_phone: str | None = Field(default=None, min_length=8, max_length=32)


class MessageResponse(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str
    exp: datetime


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    email: str
    role: str
    created_at: datetime
