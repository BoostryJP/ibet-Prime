"""v23.6.0_feature_513

Revision ID: 90b5d4040e8f
Revises: a1e5a5a6745e
Create Date: 2023-04-26 09:44:52.193833

"""
import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "90b5d4040e8f"
down_revision = "a1e5a5a6745e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "idx_lock",
        sa.Column("msg_sender", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_lock_msg_sender"),
        "idx_lock",
        ["msg_sender"],
        unique=False,
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_unlock",
        sa.Column("msg_sender", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_unlock_msg_sender"),
        "idx_unlock",
        ["msg_sender"],
        unique=False,
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_idx_unlock_msg_sender"),
        table_name="idx_unlock",
        schema=get_db_schema(),
    )
    op.drop_column("idx_unlock", "msg_sender", schema=get_db_schema())
    op.drop_index(
        op.f("ix_idx_lock_msg_sender"), table_name="idx_lock", schema=get_db_schema()
    )
    op.drop_column("idx_lock", "msg_sender", schema=get_db_schema())
    # ### end Alembic commands ###