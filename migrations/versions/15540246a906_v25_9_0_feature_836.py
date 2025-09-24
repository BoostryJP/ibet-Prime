"""v25_9_0_feature_836

Revision ID: 15540246a906
Revises: 87da0053664a
Create Date: 2025-07-10 12:45:04.072476

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "15540246a906"
down_revision = "87da0053664a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ethereum_node",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("endpoint_uri", sa.String(length=267), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("is_synced", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("ethereum_node", schema=get_db_schema())
