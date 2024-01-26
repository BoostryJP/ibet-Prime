"""v0.1.0_feature_56

Revision ID: bb5d903f97f2
Revises: fac5912d12bd
Create Date: 2021-04-26 17:51:36.827771

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "bb5d903f97f2"
down_revision = "fac5912d12bd"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "node",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("is_synced", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("node", schema=get_db_schema())
    # ### end Alembic commands ###
