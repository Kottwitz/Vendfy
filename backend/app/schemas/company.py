from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CompanyUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    whatsapp_phone_number_id: str | None = Field(
        default=None, pattern=r"^\d+$", max_length=100
    )
    whatsapp_access_token: str | None = Field(default=None, max_length=4096)
    clear_whatsapp_access_token: bool = False
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, max_length=320)
    smtp_password: str | None = Field(default=None, max_length=4096)
    clear_smtp_password: bool = False
    smtp_security: Literal["starttls", "ssl"] = "starttls"

    @field_validator(
        "name",
        "document",
        "phone",
        "address",
        "whatsapp_phone_number_id",
        "whatsapp_access_token",
        "smtp_host",
        "smtp_username",
        "smtp_password",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    document: str | None
    phone: str | None
    email: str | None
    address: str | None
    whatsapp_phone_number_id: str | None
    whatsapp_configured: bool
    smtp_host: str | None
    smtp_port: int | None
    smtp_username: str | None
    smtp_security: Literal["starttls", "ssl"]
    smtp_configured: bool
