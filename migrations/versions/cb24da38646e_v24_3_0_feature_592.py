"""v24_3_0_feature_592

Revision ID: cb24da38646e
Revises: 6814beab6ff6
Create Date: 2024-02-07 17:13:14.601480

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "cb24da38646e"
down_revision = "6814beab6ff6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "token",
        sa.Column("initial_position_synced", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(
        sa.text(f"UPDATE token SET initial_position_synced = 'true';")
    )


def downgrade():
    op.drop_column("token", "initial_position_synced", schema=get_db_schema())
