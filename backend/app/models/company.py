from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.quote import Quote
    from app.models.user import User


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("document", name="uq_companies_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    document: Mapped[str | None] = mapped_column(String(32))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    logo: Mapped[str | None] = mapped_column(String(2048))
    address: Mapped[str | None] = mapped_column(String(500))
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(100))
    whatsapp_access_token_encrypted: Mapped[str | None] = mapped_column(String(8192))
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_port: Mapped[int | None] = mapped_column(Integer)
    smtp_username: Mapped[str | None] = mapped_column(String(320))
    smtp_password_encrypted: Mapped[str | None] = mapped_column(String(8192))
    smtp_security: Mapped[str] = mapped_column(
        String(16), nullable=False, default="starttls", server_default="starttls"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    users: Mapped[list[User]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )
    clients: Mapped[list[Client]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )
    quotes: Mapped[list[Quote]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )
