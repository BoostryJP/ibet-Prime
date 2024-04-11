"""v24_6_0_feature_606_1

Revision ID: 346d0e814893
Revises: a748dd5d4119
Create Date: 2024-04-11 14:29:27.434855

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "346d0e814893"
down_revision = "a748dd5d4119"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idx_delivery",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("delivery_id", sa.BigInteger(), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_address", sa.String(length=42), nullable=False),
        sa.Column("seller_address", sa.String(length=42), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("agent_address", sa.String(length=42), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("create_blocktimestamp", sa.DateTime(), nullable=False),
        sa.Column("create_transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("cancel_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("cancel_transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("confirm_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("confirm_transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("finish_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("finish_transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("abort_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("abort_transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("status", sa.BigInteger(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_abort_transaction_hash"),
        "idx_delivery",
        ["abort_transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_agent_address"),
        "idx_delivery",
        ["agent_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_cancel_transaction_hash"),
        "idx_delivery",
        ["cancel_transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_confirm_transaction_hash"),
        "idx_delivery",
        ["confirm_transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_create_transaction_hash"),
        "idx_delivery",
        ["create_transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_delivery_id"),
        "idx_delivery",
        ["delivery_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_exchange_address"),
        "idx_delivery",
        ["exchange_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_finish_transaction_hash"),
        "idx_delivery",
        ["finish_transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_seller_address"),
        "idx_delivery",
        ["seller_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_delivery_token_address"),
        "idx_delivery",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_delivery_block_number",
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("exchange_address"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("idx_delivery_block_number", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_delivery_token_address"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_seller_address"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_finish_transaction_hash"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_exchange_address"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_delivery_id"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_create_transaction_hash"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_confirm_transaction_hash"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_cancel_transaction_hash"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_agent_address"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_delivery_abort_transaction_hash"),
        table_name="idx_delivery",
        schema=get_db_schema(),
    )
    op.drop_table("idx_delivery", schema=get_db_schema())
