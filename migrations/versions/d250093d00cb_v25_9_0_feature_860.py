"""v25_9_0_feature_860

Revision ID: d250093d00cb
Revises: 455ab6ac9dc5
Create Date: 2025-08-04 18:50:52.485637

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "d250093d00cb"
down_revision = "455ab6ac9dc5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idx_eth_ibet_wst_whitelist",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=False),
        sa.Column("st_account_address", sa.String(length=42), nullable=False),
        sa.Column("sc_account_address", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint(
            "ibet_wst_address", "st_account_address", "sc_account_address"
        ),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("idx_eth_ibet_wst_whitelist", schema=get_db_schema())
