"""v25_9_0_feature_821

Revision ID: adf5d22deadf
Revises: a042318eac16
Create Date: 2025-06-25 16:56:33.361659

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "adf5d22deadf"
down_revision = "a042318eac16"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idx_eth_ibet_wst_trade",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=False),
        sa.Column("index", sa.BigInteger(), nullable=False),
        sa.Column("seller_st_account_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_st_account_address", sa.String(length=42), nullable=False),
        sa.Column("sc_token_address", sa.String(length=42), nullable=False),
        sa.Column("seller_sc_account_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_sc_account_address", sa.String(length=42), nullable=False),
        sa.Column("st_value", sa.BigInteger(), nullable=False),
        sa.Column("sc_value", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ibet_wst_address", "index"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_buyer_sc_account_address"),
        "idx_eth_ibet_wst_trade",
        ["buyer_sc_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_buyer_st_account_address"),
        "idx_eth_ibet_wst_trade",
        ["buyer_st_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_sc_token_address"),
        "idx_eth_ibet_wst_trade",
        ["sc_token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_seller_sc_account_address"),
        "idx_eth_ibet_wst_trade",
        ["seller_sc_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_seller_st_account_address"),
        "idx_eth_ibet_wst_trade",
        ["seller_st_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_eth_ibet_wst_trade_state"),
        "idx_eth_ibet_wst_trade",
        ["state"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_eth_ibet_wst_trade_block_number",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("idx_eth_ibet_wst_trade_block_number", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_state"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_seller_st_account_address"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_seller_sc_account_address"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_sc_token_address"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_buyer_st_account_address"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_eth_ibet_wst_trade_buyer_sc_account_address"),
        table_name="idx_eth_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_table("idx_eth_ibet_wst_trade", schema=get_db_schema())
