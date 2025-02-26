"""v25_3_0_fix_763_2

Revision ID: 40e3e7206fbc
Revises: 18506373ccd3
Create Date: 2025-02-26 12:33:20.263287

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "40e3e7206fbc"
down_revision = "18506373ccd3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_locked_position_token_account_value_modified",
        "idx_locked_position",
        ["token_address", "account_address", "value", "modified"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        "idx_personal_info_issuer_account",
        "idx_personal_info",
        ["issuer_address", "account_address"],
        unique=False,
        postgresql_include=["personal_info", "data_source", "created", "modified"],
        schema=get_db_schema(),
    )
    op.create_index(
        "idx_position_token_account",
        "idx_position",
        ["token_address", "account_address"],
        unique=False,
        postgresql_include=[
            "balance",
            "exchange_balance",
            "exchange_commitment",
            "pending_transfer",
            "created",
            "modified",
        ],
        schema=get_db_schema(),
    )
    op.create_index(
        "idx_position_token_account_value",
        "idx_position",
        [
            "token_address",
            "account_address",
            "balance",
            "exchange_balance",
            "pending_transfer",
            "exchange_commitment",
        ],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        "idx_position_token_account_value",
        table_name="idx_position",
        schema=get_db_schema(),
    )
    op.drop_index(
        "idx_position_token_account",
        table_name="idx_position",
        postgresql_include=[
            "balance",
            "exchange_balance",
            "exchange_commitment",
            "pending_transfer",
            "created",
            "modified",
        ],
        schema=get_db_schema(),
    )
    op.drop_index(
        "idx_personal_info_issuer_account",
        table_name="idx_personal_info",
        postgresql_include=["personal_info", "data_source", "created", "modified"],
        schema=get_db_schema(),
    )
    op.drop_index(
        "idx_locked_position_token_account_value_modified",
        table_name="idx_locked_position",
        schema=get_db_schema(),
    )
