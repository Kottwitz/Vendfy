from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuoteStatus

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.company import Company
    from app.models.quote_item import QuoteItem


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_quotes_company_number"),
        CheckConstraint("number > 0", name="ck_quotes_number_positive"),
        CheckConstraint("subtotal >= 0", name="ck_quotes_subtotal_nonnegative"),
        CheckConstraint("discount >= 0", name="ck_quotes_discount_nonnegative"),
        CheckConstraint("total >= 0", name="ck_quotes_total_nonnegative"),
        Index("ix_quotes_company_status", "company_id", "status"),
        Index("ix_quotes_company_client", "company_id", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_quotes_company_id"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT", name="fk_quotes_client_id"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(
            QuoteStatus,
            name="quote_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=QuoteStatus.DRAFT,
        server_default=QuoteStatus.DRAFT.value,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    description: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    company: Mapped[Company] = relationship(back_populates="quotes")
    client: Mapped[Client] = relationship(back_populates="quotes")
    items: Mapped[list[QuoteItem]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", passive_deletes=True
    )
