"""v24_9_0_feature_606_3

Revision ID: f237571559e6
Revises: 5c13eac558a4
Create Date: 2024-08-03 18:02:50.022375

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "f237571559e6"
down_revision = "5c13eac558a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dvp_async_process",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("process_type", sa.String(length=30), nullable=False),
        sa.Column("process_status", sa.Integer(), nullable=False),
        sa.Column("dvp_contract_address", sa.String(length=42), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("seller_address", sa.String(length=42), nullable=False),
        sa.Column("buyer_address", sa.String(length=42), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("agent_address", sa.String(length=42), nullable=False),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("delivery_id", sa.BigInteger(), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("step_tx_hash", sa.String(length=66), nullable=True),
        sa.Column("step_tx_status", sa.String(length=10), nullable=True),
        sa.Column("revert_tx_hash", sa.String(length=66), nullable=True),
        sa.Column("revert_tx_status", sa.String(length=10), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_dvp_async_process_process_status"),
        "dvp_async_process",
        ["process_status"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_dvp_async_process_revert_tx_status"),
        "dvp_async_process",
        ["revert_tx_status"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_dvp_async_process_step_tx_status"),
        "dvp_async_process",
        ["step_tx_status"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_dvp_async_process_step_tx_status"),
        table_name="dvp_async_process",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_dvp_async_process_revert_tx_status"),
        table_name="dvp_async_process",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_dvp_async_process_process_status"),
        table_name="dvp_async_process",
        schema=get_db_schema(),
    )
    op.drop_table("dvp_async_process", schema=get_db_schema())
