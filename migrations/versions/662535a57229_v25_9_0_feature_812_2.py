"""v25_9_0_feature_812_2

Revision ID: 662535a57229
Revises: 15540246a906
Create Date: 2025-07-14 17:07:03.881845

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "662535a57229"
down_revision = "15540246a906"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "eth_ibet_wst_tx",
        sa.Column("client_ip", sa.String(length=40), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("eth_ibet_wst_tx", "client_ip", schema=get_db_schema())
