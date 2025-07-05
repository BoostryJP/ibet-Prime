"""v25_9_0_feature_822_2

Revision ID: 87da0053664a
Revises: 3479579bb909
Create Date: 2025-07-05 15:33:41.805699

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "87da0053664a"
down_revision = "3479579bb909"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "eth_ibet_wst_tx",
        sa.Column("event_log", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("eth_ibet_wst_tx", "event_log", schema=get_db_schema())
