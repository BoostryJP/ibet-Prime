"""v25_9_0_feature_812_3

Revision ID: cfb5c6ce3197
Revises: 662535a57229
Create Date: 2025-07-15 08:33:07.078589

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "cfb5c6ce3197"
down_revision = "662535a57229"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "eth_ibet_wst_tx",
        sa.Column("gas_used", sa.BigInteger(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("eth_ibet_wst_tx", "gas_used", schema=get_db_schema())
