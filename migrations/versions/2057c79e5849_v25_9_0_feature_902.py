"""v25_9_0_feature_902

Revision ID: 2057c79e5849
Revises: b8410588fcb8
Create Date: 2025-09-09 23:13:07.107279

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "2057c79e5849"
down_revision = "b8410588fcb8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dvp_agent_account",
        sa.Column("dedicated_agent_id", sa.String(length=100), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_delivery",
        sa.Column("dedicated_agent_id", sa.String(length=100), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("idx_delivery", "dedicated_agent_id", schema=get_db_schema())
    op.drop_column("dvp_agent_account", "dedicated_agent_id", schema=get_db_schema())
