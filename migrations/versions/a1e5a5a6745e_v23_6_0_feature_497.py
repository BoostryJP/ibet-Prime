"""v23_6_0_feature_497

Revision ID: a1e5a5a6745e
Revises: 7d09371c365e
Create Date: 2023-04-01 14:53:28.859908

"""
import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "a1e5a5a6745e"
down_revision = "7d09371c365e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "idx_transfer_approval",
        sa.Column("cancellation_blocktimestamp", sa.DateTime(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "idx_transfer_approval", "cancellation_blocktimestamp", schema=get_db_schema()
    )
