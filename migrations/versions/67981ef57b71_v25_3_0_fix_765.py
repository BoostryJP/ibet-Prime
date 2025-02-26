"""v25_3_0_fix_765

Revision ID: 67981ef57b71
Revises: 40e3e7206fbc
Create Date: 2025-02-26 14:19:01.323801

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "67981ef57b71"
down_revision = "40e3e7206fbc"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "token_holder_extra_info",
        "external_id_1_type",
        new_column_name="external_id1_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id_1",
        new_column_name="external_id1",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id_2_type",
        new_column_name="external_id2_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id_2",
        new_column_name="external_id2",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id_3_type",
        new_column_name="external_id3_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id_3",
        new_column_name="external_id3",
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "token_holder_extra_info",
        "external_id1_type",
        new_column_name="external_id_1_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id1",
        new_column_name="external_id_1",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id2_type",
        new_column_name="external_id_2_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id2",
        new_column_name="external_id_2",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id3_type",
        new_column_name="external_id_3_type",
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holder_extra_info",
        "external_id3",
        new_column_name="external_id_3",
        schema=get_db_schema(),
    )
