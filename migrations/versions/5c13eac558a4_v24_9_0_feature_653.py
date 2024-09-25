"""v24_9_0_feature_653

Revision ID: 5c13eac558a4
Revises: 4704529e8fe0
Create Date: 2024-07-04 20:54:23.011549

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "5c13eac558a4"
down_revision = "4704529e8fe0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bulk_transfer_upload",
        sa.Column("token_address", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.drop_column(
        "bulk_transfer_upload", "transaction_compression", schema=get_db_schema()
    )


def downgrade():
    op.add_column(
        "bulk_transfer_upload",
        sa.Column(
            "transaction_compression", sa.BOOLEAN(), autoincrement=False, nullable=True
        ),
        schema=get_db_schema(),
    )
    op.drop_column("bulk_transfer_upload", "token_address", schema=get_db_schema())
