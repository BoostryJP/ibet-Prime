"""v21.12.0_feature/#222

Revision ID: 9c694b5e95aa
Revises: 52b9095d9dff
Create Date: 2021-10-18 13:54:40.783076

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "9c694b5e95aa"
down_revision = "52b9095d9dff"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "idx_position",
        sa.Column("exchange_balance", sa.BigInteger(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_position",
        sa.Column("exchange_commitment", sa.BigInteger(), nullable=True),
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("idx_position", "exchange_commitment", schema=get_db_schema())
    op.drop_column("idx_position", "exchange_balance", schema=get_db_schema())
    # ### end Alembic commands ###
