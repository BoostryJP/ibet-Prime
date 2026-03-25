"""v26_3_0_feature_950

Revision ID: 84cb5764c09a
Revises: 39661c5c4bac
Create Date: 2025-12-29 14:39:38.279754

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "84cb5764c09a"
down_revision = "39661c5c4bac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_block_data_has_transactions",
        "block_data",
        ["number"],
        unique=False,
        postgresql_where=sa.text(
            "transactions IS NOT NULL AND json_array_length(transactions) > 0"
        ),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        "ix_block_data_has_transactions",
        table_name="block_data",
        postgresql_where=sa.text(
            "transactions IS NOT NULL AND json_array_length(transactions) > 0"
        ),
        schema=get_db_schema(),
    )
