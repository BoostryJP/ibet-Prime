"""v25_9_0_feature_860

Revision ID: 2aafdb33f3d1
Revises: 455ab6ac9dc5
Create Date: 2025-07-26 22:40:17.613731

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "2aafdb33f3d1"
down_revision = "455ab6ac9dc5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idx_eth_ibet_wst_whitelist",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ibet_wst_address", "account_address"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("idx_eth_ibet_wst_whitelist", schema=get_db_schema())
