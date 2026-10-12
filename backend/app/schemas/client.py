from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    document: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    document: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> "ClientUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null.")
        return self


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    phone: str | None
    email: str | None
    document: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime
