"""v24_6_0_feature_637

Revision ID: 4704529e8fe0
Revises: 0656c408ebbb
Create Date: 2024-06-04 17:46:03.131011

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import delete


from app.database import get_db_schema
from app.model.db import IDXPersonalInfoHistory

# revision identifiers, used by Alembic.
revision = "4704529e8fe0"
down_revision = "0656c408ebbb"
branch_labels = None
depends_on = None


def upgrade():
    # Delete all `idx_personal_info_history` data
    op.get_bind().execute(delete(IDXPersonalInfoHistory))
    op.add_column(
        "idx_personal_info_history",
        sa.Column("block_timestamp", sa.DateTime(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "idx_personal_info_history", "block_timestamp", schema=get_db_schema()
    )
