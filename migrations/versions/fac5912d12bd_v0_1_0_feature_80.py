"""v0.1.0_feature_80

Revision ID: fac5912d12bd
Revises: 2eee006a38d5
Create Date: 2021-04-22 13:21:29.426107

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "fac5912d12bd"
down_revision = "2eee006a38d5"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "idx_transfer_approval",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=True),
        sa.Column("application_id", sa.BigInteger(), nullable=True),
        sa.Column("from_address", sa.String(length=42), nullable=True),
        sa.Column("to_address", sa.String(length=42), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("application_datetime", sa.DateTime(), nullable=True),
        sa.Column("application_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("approval_datetime", sa.DateTime(), nullable=True),
        sa.Column("approval_blocktimestamp", sa.DateTime(), nullable=True),
        sa.Column("cancelled", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_transfer_approval_application_id"),
        "idx_transfer_approval",
        ["application_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_transfer_approval_token_address"),
        "idx_transfer_approval",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_position",
        sa.Column("pending_transfer", sa.BigInteger(), nullable=True),
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("idx_position", "pending_transfer", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_transfer_approval_token_address"),
        table_name="idx_transfer_approval",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_transfer_approval_application_id"),
        table_name="idx_transfer_approval",
        schema=get_db_schema(),
    )
    op.drop_table("idx_transfer_approval", schema=get_db_schema())
    # ### end Alembic commands ###
