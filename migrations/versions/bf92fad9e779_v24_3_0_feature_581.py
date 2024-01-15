"""v24_3_0_feature_581

Revision ID: bf92fad9e779
Revises: 679359eceb76
Create Date: 2024-01-13 23:40:17.663410

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "bf92fad9e779"
down_revision = "679359eceb76"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "bulk_transfer",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        autoincrement=True,
        schema=get_db_schema(),
    )
    op.add_column(
        "bulk_transfer_upload",
        sa.Column("transaction_compression", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "bulk_transfer_upload", "transaction_compression", schema=get_db_schema()
    )
    op.alter_column(
        "bulk_transfer",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
        autoincrement=True,
        schema=get_db_schema(),
    )
