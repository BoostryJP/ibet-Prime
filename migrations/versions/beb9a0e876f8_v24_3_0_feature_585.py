"""v24_3_0_feature_585

Revision ID: beb9a0e876f8
Revises: bf92fad9e779
Create Date: 2024-01-16 17:28:12.921265

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "beb9a0e876f8"
down_revision = "bf92fad9e779"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bulk_transfer",
        sa.Column("transaction_error_code", sa.Integer(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "bulk_transfer",
        sa.Column("transaction_error_message", sa.String(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("bulk_transfer", "transaction_error_message", schema=get_db_schema())
    op.drop_column("bulk_transfer", "transaction_error_code", schema=get_db_schema())
