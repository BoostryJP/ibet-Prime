"""v26_6_0_feature_1001_2

Revision ID: 4ded95375da2
Revises: 7b965ee0f8f1
Create Date: 2026-04-10 10:08:49.952551

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "4ded95375da2"
down_revision = "7b965ee0f8f1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "batch_issue_redeem",
        "upload_id",
        existing_type=sa.VARCHAR(length=36),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "batch_issue_redeem",
        "upload_id",
        existing_type=sa.VARCHAR(length=36),
        nullable=True,
        schema=get_db_schema(),
    )
