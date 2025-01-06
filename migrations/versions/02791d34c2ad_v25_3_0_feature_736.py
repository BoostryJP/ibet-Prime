"""v25_3_0_feature_736

Revision ID: 02791d34c2ad
Revises: 3b7e17706e3e
Create Date: 2025-01-06 18:41:14.077404

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "02791d34c2ad"
down_revision = "3b7e17706e3e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "batch_register_personal_info_upload",
        sa.Column("token_address", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "batch_register_personal_info_upload", "token_address", schema=get_db_schema()
    )
