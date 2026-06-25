"""v26_6_0_feature_1001

Revision ID: 7b965ee0f8f1
Revises: 301b31d8c870
Create Date: 2026-04-09 20:50:41.056799

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "7b965ee0f8f1"
down_revision = "301b31d8c870"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "rsa_status",
        existing_type=sa.INTEGER(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "freeze_log_account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "freeze_log_account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "freeze_log_account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "freeze_log_account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "freeze_log_account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "freeze_log_account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "rsa_status",
        existing_type=sa.INTEGER(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        schema=get_db_schema(),
    )
