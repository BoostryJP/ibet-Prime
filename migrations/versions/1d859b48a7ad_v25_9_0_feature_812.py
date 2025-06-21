"""v25_9_0_feature_812

Revision ID: 1d859b48a7ad
Revises: a7db3bfbfe9e
Create Date: 2025-06-20 21:31:34.261489

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "1d859b48a7ad"
down_revision = "a7db3bfbfe9e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "eth_ibet_wst_tx",
        sa.Column("tx_id", sa.String(length=36), nullable=False),
        sa.Column("tx_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=2), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("tx_params", sa.JSON(), nullable=False),
        sa.Column("tx_sender", sa.String(length=42), nullable=False),
        sa.Column("authorizer", sa.String(length=42), nullable=True),
        sa.Column("authorization", sa.JSON(), nullable=True),
        sa.Column("tx_hash", sa.String(length=66), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("finalized", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("tx_id"),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_activated", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_version", sa.String(length=2), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_tx_id", sa.String(length=36), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_deployed", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("token", "ibet_wst_address", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_deployed", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_tx_id", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_version", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_activated", schema=get_db_schema())
    op.drop_table("eth_ibet_wst_tx", schema=get_db_schema())
