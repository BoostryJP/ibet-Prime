"""v22_9_0_feature_383

Revision ID: b1844596cae5
Revises: 3a809fa594f8
Create Date: 2022-09-05 19:31:48.858899

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "b1844596cae5"
down_revision = "3a809fa594f8"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE upload_file SET label = '' WHERE label IS NULL;")
    op.alter_column(
        "upload_file",
        "label",
        existing_type=sa.VARCHAR(length=200),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.execute("UPDATE upload_file SET label = NULL WHERE label = '';")
    op.alter_column(
        "upload_file",
        "label",
        existing_type=sa.VARCHAR(length=200),
        nullable=True,
        schema=get_db_schema(),
    )
