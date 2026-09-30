"""v26_12_0_transfer_history_indexes

Revision ID: a38e9c71d6b2
Revises: ded62b5c16ca
Create Date: 2026-09-30

"""

from alembic import op
import sqlalchemy as sa

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "a38e9c71d6b2"
down_revision = "ded62b5c16ca"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_idx_transfer_token_from_timestamp_id",
        "idx_transfer",
        [
            "token_address",
            "from_address",
            sa.text("block_timestamp DESC"),
            sa.text("id DESC"),
        ],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_idx_transfer_token_to_timestamp_id",
        "idx_transfer",
        [
            "token_address",
            "to_address",
            sa.text("block_timestamp DESC"),
            sa.text("id DESC"),
        ],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        "ix_idx_transfer_token_to_timestamp_id",
        table_name="idx_transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        "ix_idx_transfer_token_from_timestamp_id",
        table_name="idx_transfer",
        schema=get_db_schema(),
    )
