"""Require email verification for newly registered users."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261012_05"
down_revision: str | None = "20261012_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE users SET email_verified = TRUE")
    op.alter_column(
        "users",
        "email_verified",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_email_verification_token_hash",
        "users",
        ["email_verification_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_email_verification_token_hash", table_name="users")
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
