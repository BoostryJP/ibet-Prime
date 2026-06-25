"""v26_6_0_feature_1014

Revision ID: c2f7c9e8a1b4
Revises: 5f2c9a8d1e41
Create Date: 2026-04-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "c2f7c9e8a1b4"
down_revision = "5f2c9a8d1e41"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ava_ibet_wst_tx",
        sa.Column("tx_id", sa.String(length=36), nullable=False),
        sa.Column("tx_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=2), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=True),
        sa.Column("tx_params", sa.JSON(), nullable=False),
        sa.Column("tx_sender", sa.String(length=42), nullable=False),
        sa.Column("authorizer", sa.String(length=42), nullable=True),
        sa.Column("authorization", sa.JSON(), nullable=True),
        sa.Column("client_ip", sa.String(length=40), nullable=True),
        sa.Column("tx_nonce", sa.BigInteger(), nullable=True),
        sa.Column("tx_hash", sa.String(length=66), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("gas_used", sa.BigInteger(), nullable=True),
        sa.Column("finalized", sa.Boolean(), nullable=False),
        sa.Column("event_log", sa.JSON(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("tx_id"),
        schema=get_db_schema(),
    )

    op.create_table(
        "ava_to_ibet_bridge_tx",
        sa.Column("tx_id", sa.String(length=36), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("tx_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("tx_params", sa.JSON(), nullable=False),
        sa.Column("tx_sender", sa.String(length=42), nullable=False),
        sa.Column("tx_hash", sa.String(length=66), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("tx_id"),
        schema=get_db_schema(),
    )

    op.create_table(
        "idx_ava_ibet_wst_trade",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=False),
        sa.Column("index", sa.BigInteger(), nullable=False),
        sa.Column("seller_st_account_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_st_account_address", sa.String(length=42), nullable=False),
        sa.Column("sc_token_address", sa.String(length=42), nullable=False),
        sa.Column("seller_sc_account_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_sc_account_address", sa.String(length=42), nullable=False),
        sa.Column("st_value", sa.BigInteger(), nullable=False),
        sa.Column("sc_value", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ibet_wst_address", "index"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_buyer_sc_account_address"),
        "idx_ava_ibet_wst_trade",
        ["buyer_sc_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_buyer_st_account_address"),
        "idx_ava_ibet_wst_trade",
        ["buyer_st_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_sc_token_address"),
        "idx_ava_ibet_wst_trade",
        ["sc_token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_seller_sc_account_address"),
        "idx_ava_ibet_wst_trade",
        ["seller_sc_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_seller_st_account_address"),
        "idx_ava_ibet_wst_trade",
        ["seller_st_account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_ava_ibet_wst_trade_state"),
        "idx_ava_ibet_wst_trade",
        ["state"],
        unique=False,
        schema=get_db_schema(),
    )

    op.create_table(
        "idx_ava_ibet_wst_trade_block_number",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )

    op.create_table(
        "idx_ava_ibet_wst_whitelist",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=False),
        sa.Column("st_account_address", sa.String(length=42), nullable=False),
        sa.Column("sc_account_address_in", sa.String(length=42), nullable=False),
        sa.Column("sc_account_address_out", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ibet_wst_address", "st_account_address"),
        schema=get_db_schema(),
    )

    op.create_table(
        "avalanche_node",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("endpoint_uri", sa.String(length=267), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("is_synced", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("idx_ava_ibet_wst_whitelist", schema=get_db_schema())
    op.drop_table("idx_ava_ibet_wst_trade_block_number", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_state"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_seller_st_account_address"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_seller_sc_account_address"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_sc_token_address"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_buyer_st_account_address"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_ava_ibet_wst_trade_buyer_sc_account_address"),
        table_name="idx_ava_ibet_wst_trade",
        schema=get_db_schema(),
    )
    op.drop_table("idx_ava_ibet_wst_trade", schema=get_db_schema())
    op.drop_table("ava_to_ibet_bridge_tx", schema=get_db_schema())
    op.drop_table("ava_ibet_wst_tx", schema=get_db_schema())
    op.drop_table("avalanche_node", schema=get_db_schema())
