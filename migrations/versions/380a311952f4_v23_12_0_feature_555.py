"""v23_12_0_feature_555

Revision ID: 380a311952f4
Revises: 53caec5f4dce
Create Date: 2023-11-08 11:20:47.891601

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "380a311952f4"
down_revision = "53caec5f4dce"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "transfer_approval_history",
        sa.Column("from_address_personal_info", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "transfer_approval_history",
        sa.Column("to_address_personal_info", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "transfer_approval_history", "to_address_personal_info", schema=get_db_schema()
    )
    op.drop_column(
        "transfer_approval_history",
        "from_address_personal_info",
        schema=get_db_schema(),
    )
