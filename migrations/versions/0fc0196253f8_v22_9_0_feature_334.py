"""v22_9_0_feature_334

Revision ID: 0fc0196253f8
Revises: 7fe46c2af01e
Create Date: 2022-07-06 16:46:51.725890

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "0fc0196253f8"
down_revision = "7fe46c2af01e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("additional_token_info", schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "additional_token_info",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "token_address", sa.VARCHAR(length=42), autoincrement=False, nullable=False
        ),
        sa.Column(
            "is_manual_transfer_approval",
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("token_address", name="additional_token_info_pkey"),
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###
