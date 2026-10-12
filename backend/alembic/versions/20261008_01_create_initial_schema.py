"""Create initial Vendfy data model.

Revision ID: 20261008_01
Revises:
Create Date: 2026-10-08 13:40:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261008_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


quote_status = postgresql.ENUM(
    "DRAFT",
    "SENT",
    "VIEWED",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    name="quote_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    quote_status.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("logo", sa.String(length=2048), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("document", name="uq_companies_document"),
    )
    op.create_table(
        "clients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("document", sa.String(length=32), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_clients_company_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_clients"),
        sa.UniqueConstraint(
            "company_id", "document", name="uq_clients_company_document"
        ),
    )
    op.create_index("ix_clients_company_id", "clients", ["company_id"])
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_users_company_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("company_id", "email", name="uq_users_company_email"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_table(
        "quotes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            quote_status,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column(
            "subtotal", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column(
            "discount", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column(
            "total", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("number > 0", name="ck_quotes_number_positive"),
        sa.CheckConstraint("subtotal >= 0", name="ck_quotes_subtotal_nonnegative"),
        sa.CheckConstraint("discount >= 0", name="ck_quotes_discount_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_quotes_total_nonnegative"),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_quotes_client_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_quotes_company_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quotes"),
        sa.UniqueConstraint("company_id", "number", name="uq_quotes_company_number"),
    )
    op.create_index(
        "ix_quotes_company_status", "quotes", ["company_id", "status"]
    )
    op.create_index(
        "ix_quotes_company_client", "quotes", ["company_id", "client_id"]
    )
    op.create_table(
        "quote_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name="ck_quote_items_quantity_positive"
        ),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_quote_items_unit_price_nonnegative"
        ),
        sa.CheckConstraint(
            "total >= 0", name="ck_quote_items_total_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name="fk_quote_items_quote_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quote_items"),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_items_quote_id", table_name="quote_items")
    op.drop_table("quote_items")
    op.drop_index("ix_quotes_company_client", table_name="quotes")
    op.drop_index("ix_quotes_company_status", table_name="quotes")
    op.drop_table("quotes")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_clients_company_id", table_name="clients")
    op.drop_table("clients")
    op.drop_table("companies")
    quote_status.drop(op.get_bind(), checkfirst=True)
