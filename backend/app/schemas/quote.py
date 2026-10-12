from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import QuoteStatus

Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
UnitPrice = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
UnitCost = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class QuoteItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Quantity
    unit_price: UnitPrice
    unit_cost: UnitCost | None = None


class QuoteItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    quantity: Quantity | None = None
    unit_price: UnitPrice | None = None
    unit_cost: UnitCost | None = None

    @model_validator(mode="after")
    def item_fields_cannot_be_null(self) -> "QuoteItemUpdate":
        for field in ("description", "quantity", "unit_price"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class QuoteCreate(BaseModel):
    client_id: UUID
    items: list[QuoteItemCreate] = Field(default_factory=list, max_length=500)
    discount: Money = Decimal("0.00")
    description: str | None = None
    valid_until: date | None = None


class QuoteUpdate(BaseModel):
    client_id: UUID | None = None
    items: list[QuoteItemCreate] | None = Field(default=None, max_length=500)
    discount: Money | None = None
    description: str | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def non_nullable_fields_cannot_be_null(self) -> "QuoteUpdate":
        for field in ("client_id", "discount", "items"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class QuoteItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    unit_cost: Decimal | None
    total: Decimal


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    client_id: UUID
    number: int
    status: QuoteStatus
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    description: str | None
    valid_until: date | None
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemResponse]


class QuoteStatusUpdate(BaseModel):
    status: QuoteStatus


class QuoteFinancialSummary(BaseModel):
    gross_revenue: Decimal
    expenses: Decimal
    profit: Decimal
    missing_cost_items: int
