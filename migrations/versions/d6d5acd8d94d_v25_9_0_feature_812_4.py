"""v25_9_0_feature_812_4

Revision ID: d6d5acd8d94d
Revises: d250093d00cb
Create Date: 2025-08-05 14:52:40.675398

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "d6d5acd8d94d"
down_revision = "d250093d00cb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "idx_eth_ibet_wst_whitelist",
        sa.Column("sc_account_address_in", sa.String(length=42), nullable=False),
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_eth_ibet_wst_whitelist",
        sa.Column("sc_account_address_out", sa.String(length=42), nullable=False),
        schema=get_db_schema(),
    )
    op.drop_column(
        "idx_eth_ibet_wst_whitelist", "sc_account_address", schema=get_db_schema()
    )


def downgrade():
    op.add_column(
        "idx_eth_ibet_wst_whitelist",
        sa.Column(
            "sc_account_address",
            sa.VARCHAR(length=42),
            autoincrement=False,
            nullable=False,
        ),
        schema=get_db_schema(),
    )
    op.drop_column(
        "idx_eth_ibet_wst_whitelist", "sc_account_address_out", schema=get_db_schema()
    )
    op.drop_column(
        "idx_eth_ibet_wst_whitelist", "sc_account_address_in", schema=get_db_schema()
    )
