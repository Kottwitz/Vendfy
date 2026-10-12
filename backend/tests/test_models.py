from decimal import Decimal

from sqlalchemy import Numeric, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.models import Client, Company, Quote, QuoteItem, QuoteStatus, User


def test_models_register_with_expected_tables_and_relationships() -> None:
    configure_mappers()

    assert set(Base.metadata.tables) == {
        "companies",
        "users",
        "clients",
        "quotes",
        "quote_items",
    }
    assert Company.users.property.mapper.class_ is User
    assert Company.clients.property.mapper.class_ is Client
    assert Company.quotes.property.mapper.class_ is Quote
    assert Client.quotes.property.mapper.class_ is Quote
    assert Quote.items.property.mapper.class_ is QuoteItem
    user_table = Base.metadata.tables["users"]
    user_unique_constraints = {
        constraint.name
        for constraint in user_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_users_email" in user_unique_constraints
    assert [status.value for status in QuoteStatus] == [
        "DRAFT",
        "SENT",
        "VIEWED",
        "APPROVED",
        "REJECTED",
        "EXPIRED",
        "CANCELLED",
    ]


def test_money_columns_use_decimal_numeric_types() -> None:
    for model, column_name in (
        (Quote, "subtotal"),
        (Quote, "discount"),
        (Quote, "total"),
        (QuoteItem, "unit_price"),
        (QuoteItem, "unit_cost"),
        (QuoteItem, "total"),
    ):
        column_type = Base.metadata.tables[model.__tablename__].c[column_name].type
        assert isinstance(column_type, Numeric)
        assert column_type.asdecimal is True

    assert isinstance(Decimal("0.1") + Decimal("0.2"), Decimal)
