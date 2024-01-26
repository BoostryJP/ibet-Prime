"""v0.1.0_feature/#159

Revision ID: eb8557523406
Revises: f6056503a291
Create Date: 2021-06-28 20:20:58.229012

"""

import sqlalchemy as sa
from alembic import op

from app.database import engine, get_db_schema

# revision identifiers, used by Alembic.
revision = "eb8557523406"
down_revision = "f6056503a291"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "ledger_details_data",
        "data_id",
        existing_type=sa.String(length=42),
        type_=sa.String(length=36),
        existing_nullable=True,
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###
    if engine.name == "postgresql":
        schema = get_db_schema()
        schema = f"{schema}." if schema is not None else ""
        op.execute(
            f"ALTER INDEX {schema}ix_idx_transfer_from_to RENAME TO ix_idx_transfer_to_address"
        )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "ledger_details_data",
        "data_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=42),
        existing_nullable=True,
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###
    if engine.name == "postgresql":
        schema = get_db_schema()
        schema = f"{schema}." if schema is not None else ""
        op.execute(
            f"ALTER INDEX {schema}ix_idx_transfer_to_address RENAME TO ix_idx_transfer_from_to"
        )
