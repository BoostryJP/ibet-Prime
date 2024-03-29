"""v22.9.0.feature_339

Revision ID: 38eb462293cd
Revises: fad6669cad84
Create Date: 2022-07-11 20:36:30.195927

"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "38eb462293cd"
down_revision = "fad6669cad84"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "batch_register_personal_info",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("upload_id", sa.String(length=36), nullable=True),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("personal_info", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_batch_register_personal_info_status"),
        "batch_register_personal_info",
        ["status"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_batch_register_personal_info_upload_id"),
        "batch_register_personal_info",
        ["upload_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "batch_register_personal_info_upload",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("upload_id", sa.String(length=36), nullable=False),
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("upload_id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_batch_register_personal_info_upload_issuer_address"),
        "batch_register_personal_info_upload",
        ["issuer_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_batch_register_personal_info_upload_status"),
        "batch_register_personal_info_upload",
        ["status"],
        unique=False,
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_batch_register_personal_info_upload_status"),
        table_name="batch_register_personal_info_upload",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_batch_register_personal_info_upload_issuer_address"),
        table_name="batch_register_personal_info_upload",
        schema=get_db_schema(),
    )
    op.drop_table("batch_register_personal_info_upload", schema=get_db_schema())
    op.drop_index(
        op.f("ix_batch_register_personal_info_upload_id"),
        table_name="batch_register_personal_info",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_batch_register_personal_info_status"),
        table_name="batch_register_personal_info",
        schema=get_db_schema(),
    )
    op.drop_table("batch_register_personal_info", schema=get_db_schema())
    # ### end Alembic commands ###
