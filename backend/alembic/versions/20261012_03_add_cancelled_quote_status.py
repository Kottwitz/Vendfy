"""Add cancelled status to quotes.

Revision ID: 20261012_03
Revises: 20261012_02
Create Date: 2026-10-12
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20261012_03"
down_revision: str | None = "20261012_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE quote_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    op.execute(
        "UPDATE quotes SET status = 'REJECTED' WHERE status = 'CANCELLED'"
    )
    op.execute("ALTER TABLE quotes ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "CREATE TYPE quote_status_old AS ENUM "
        "('DRAFT', 'SENT', 'VIEWED', 'APPROVED', 'REJECTED', 'EXPIRED')"
    )
    op.execute(
        "ALTER TABLE quotes ALTER COLUMN status TYPE quote_status_old "
        "USING status::text::quote_status_old"
    )
    op.execute("DROP TYPE quote_status")
    op.execute("ALTER TYPE quote_status_old RENAME TO quote_status")
    op.execute(
        "ALTER TABLE quotes ALTER COLUMN status SET DEFAULT 'DRAFT'::quote_status"
    )
