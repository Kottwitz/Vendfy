"""Add company email and WhatsApp delivery configuration."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261012_04"
down_revision: str | None = "20261012_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("whatsapp_phone_number_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column(
            "whatsapp_access_token_encrypted",
            sa.String(length=8192),
            nullable=True,
        ),
    )
    op.add_column(
        "companies",
        sa.Column("smtp_host", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("smtp_port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("smtp_username", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("smtp_password_encrypted", sa.String(length=8192), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column(
            "smtp_security",
            sa.String(length=16),
            server_default="starttls",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "smtp_security")
    op.drop_column("companies", "smtp_password_encrypted")
    op.drop_column("companies", "smtp_username")
    op.drop_column("companies", "smtp_port")
    op.drop_column("companies", "smtp_host")
    op.drop_column("companies", "whatsapp_access_token_encrypted")
    op.drop_column("companies", "whatsapp_phone_number_id")
