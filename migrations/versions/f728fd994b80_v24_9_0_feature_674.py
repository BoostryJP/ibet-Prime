"""v24_9_0_feature_674

Revision ID: f728fd994b80
Revises: f237571559e6
Create Date: 2024-08-20 11:59:35.833321

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "f728fd994b80"
down_revision = "f237571559e6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "idx_delivery",
        sa.Column("settlement_service_type", sa.String(length=50), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("idx_delivery", "settlement_service_type", schema=get_db_schema())
