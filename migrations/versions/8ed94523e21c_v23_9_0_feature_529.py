"""v23.9.0_feature_529

Revision ID: 8ed94523e21c
Revises: fedec7fb783a
Create Date: 2023-08-07 17:22:33.511682

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import delete
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema
from app.model.db import UpdateToken

# revision identifiers, used by Alembic.
revision = "8ed94523e21c"
down_revision = "fedec7fb783a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_update_operation_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("original_contents", sa.JSON(), nullable=True),
        sa.Column("operation_category", sa.String(length=40), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_token_update_operation_log_token_address"),
        "token_update_operation_log",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.drop_column("update_token", "original_contents", schema=get_db_schema())

    # Remove All `update_token` data of which trigger attribute has "Update" value
    op.get_bind().execute(delete(UpdateToken).where(UpdateToken.trigger == "Update"))


def downgrade():
    op.add_column(
        "update_token",
        sa.Column(
            "original_contents",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_token_update_operation_log_token_address"),
        table_name="token_update_operation_log",
        schema=get_db_schema(),
    )
    op.drop_table("token_update_operation_log", schema=get_db_schema())
