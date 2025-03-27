"""v25_6_0_feature_777_1

Revision ID: a7db3bfbfe9e
Revises: e1f6370e8197
Create Date: 2025-03-25 18:16:49.007990

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update


from app.database import get_db_schema
from app.model.db import IDXLock, IDXUnlock

# revision identifiers, used by Alembic.
revision = "a7db3bfbfe9e"
down_revision = "e1f6370e8197"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "idx_lock",
        sa.Column("is_forced", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(update(IDXLock).values(is_forced=False))
    op.alter_column(
        "idx_lock",
        "is_forced",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )

    op.add_column(
        "idx_unlock",
        sa.Column("is_forced", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(update(IDXUnlock).values(is_forced=False))
    op.alter_column(
        "idx_unlock",
        "is_forced",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("idx_lock", "is_forced", schema=get_db_schema())
    op.drop_column("idx_unlock", "is_forced", schema=get_db_schema())
