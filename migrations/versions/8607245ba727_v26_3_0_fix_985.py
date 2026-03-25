"""v26_3_0_fix_985

Revision ID: 8607245ba727
Revises: 84cb5764c09a
Create Date: 2026-02-09 15:58:18.067456

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "8607245ba727"
down_revision = "84cb5764c09a"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "idx_eth_ibet_wst_trade",
        "sc_value",
        existing_type=sa.BIGINT(),
        type_=sa.Numeric(precision=78, scale=0),
        existing_nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "idx_eth_ibet_wst_trade",
        "sc_value",
        existing_type=sa.Numeric(precision=78, scale=0),
        type_=sa.BIGINT(),
        existing_nullable=False,
        schema=get_db_schema(),
    )
