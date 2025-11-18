"""v25_12_0_feature_927

Revision ID: 39661c5c4bac
Revises: 2057c79e5849
Create Date: 2025-11-18 22:11:51.898937

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "39661c5c4bac"
down_revision = "2057c79e5849"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "token",
        sa.Column("ibet_wst_name", sa.String(length=100), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("token", "ibet_wst_name", schema=get_db_schema())
