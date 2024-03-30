"""v23_3_0_feature_448

Revision ID: 6920ad60f134
Revises: e17921783d89
Create Date: 2023-01-07 23:19:30.763226

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "6920ad60f134"
down_revision = "e17921783d89"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "idx_lock",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("lock_address", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("block_timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_lock_account_address"),
        "idx_lock",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_lock_lock_address"),
        "idx_lock",
        ["lock_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_lock_token_address"),
        "idx_lock",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_lock_transaction_hash"),
        "idx_lock",
        ["transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_unlock",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("lock_address", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("recipient_address", sa.String(length=42), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("block_timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_account_address"),
        "idx_unlock",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_lock_address"),
        "idx_unlock",
        ["lock_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_recipient_address"),
        "idx_unlock",
        ["recipient_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_token_address"),
        "idx_unlock",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_transaction_hash"),
        "idx_unlock",
        ["transaction_hash"],
        unique=False,
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_idx_unlock_transaction_hash"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_unlock_token_address"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_unlock_recipient_address"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_unlock_lock_address"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_unlock_account_address"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_table("idx_unlock", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_lock_transaction_hash"),
        table_name="idx_lock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_lock_token_address"), table_name="idx_lock", schema=get_db_schema()
    )
    op.drop_index(
        op.f("ix_idx_lock_lock_address"), table_name="idx_lock", schema=get_db_schema()
    )
    op.drop_index(
        op.f("ix_idx_lock_account_address"),
        table_name="idx_lock",
        schema=get_db_schema(),
    )
    op.drop_table("idx_lock", schema=get_db_schema())
    # ### end Alembic commands ###
