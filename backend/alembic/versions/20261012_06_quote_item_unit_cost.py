"""Add optional unit cost to quote items."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261012_06"
down_revision: str | None = "20261012_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quote_items",
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quote_items", "unit_cost")
