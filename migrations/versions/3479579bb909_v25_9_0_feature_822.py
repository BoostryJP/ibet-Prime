"""v25_9_0_feature_822

Revision ID: 3479579bb909
Revises: adf5d22deadf
Create Date: 2025-06-27 21:23:06.757135

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "3479579bb909"
down_revision = "adf5d22deadf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "eth_to_ibet_bridge_tx",
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
        "ibet_wst_bridge_synced_block_number",
        sa.Column("network", sa.String(length=20), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("network"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("ibet_wst_bridge_synced_block_number", schema=get_db_schema())
    op.drop_table("eth_to_ibet_bridge_tx", schema=get_db_schema())
