"""v24_12_0_feature_708

Revision ID: f7d8342a56ea
Revises: 18a410bd19b8
Create Date: 2024-11-10 13:06:58.358270

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "f7d8342a56ea"
down_revision = "18a410bd19b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ledger_creation_request",
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("token_type", sa.String(length=40), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("request_id"),
        schema=get_db_schema(),
    )
    op.create_table(
        "ledger_creation_request_data",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("data_type", sa.String(length=20), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=True),
        sa.Column("acquisition_date", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=200), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("price", sa.BigInteger(), nullable=True),
        sa.Column("balance", sa.BigInteger(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_ledger_creation_request_data_account_address"),
        "ledger_creation_request_data",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_ledger_creation_request_data_data_type"),
        "ledger_creation_request_data",
        ["data_type"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_ledger_creation_request_data_name"),
        "ledger_creation_request_data",
        ["name"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_ledger_creation_request_data_request_id"),
        "ledger_creation_request_data",
        ["request_id"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_ledger_creation_request_data_request_id"),
        table_name="ledger_creation_request_data",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_ledger_creation_request_data_name"),
        table_name="ledger_creation_request_data",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_ledger_creation_request_data_data_type"),
        table_name="ledger_creation_request_data",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_ledger_creation_request_data_account_address"),
        table_name="ledger_creation_request_data",
        schema=get_db_schema(),
    )
    op.drop_table("ledger_creation_request_data", schema=get_db_schema())
    op.drop_table("ledger_creation_request", schema=get_db_schema())
