"""Require user email addresses to be globally unique.

Revision ID: 20261012_02
Revises: 20261008_01
Create Date: 2026-10-12
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20261012_02"
down_revision: str | None = "20261008_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_users_company_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint(
        "uq_users_company_email",
        "users",
        ["company_id", "email"],
    )
