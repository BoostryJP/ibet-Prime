"""v21.12.0_feature/#230

Revision ID: 9a178cb445c2
Revises: 8bde2ff68ed1
Create Date: 2021-12-10 10:42:25.545296

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "9a178cb445c2"
down_revision = "8bde2ff68ed1"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "additional_token_info",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("is_manual_transfer_approval", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("token_address"),
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("additional_token_info", schema=get_db_schema())
    # ### end Alembic commands ###
