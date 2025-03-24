"""v25_6_0_feature_772

Revision ID: e1f6370e8197
Revises: 67981ef57b71
Create Date: 2025-03-24 19:24:24.795378

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update

from app.database import get_db_schema
from app.model.db import ScheduledEvents

# revision identifiers, used by Alembic.
revision = "e1f6370e8197"
down_revision = "67981ef57b71"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "scheduled_events",
        sa.Column("is_soft_deleted", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(update(ScheduledEvents).values(is_soft_deleted=False))
    op.alter_column(
        "scheduled_events",
        "is_soft_deleted",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("scheduled_events", "is_soft_deleted", schema=get_db_schema())
