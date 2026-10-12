from pydantic import BaseModel, EmailStr, Field


class QuoteEmailRequest(BaseModel):
    recipient: EmailStr | None = None
    message: str | None = Field(default=None, max_length=2000)


class QuoteWhatsAppRequest(BaseModel):
    recipient_phone: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=1000)


class QuoteDeliveryResponse(BaseModel):
    detail: str
