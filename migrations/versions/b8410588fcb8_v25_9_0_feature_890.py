"""v25_9_0_feature_890

Revision ID: b8410588fcb8
Revises: d6d5acd8d94d
Create Date: 2025-08-14 15:19:45.769064

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "b8410588fcb8"
down_revision = "d6d5acd8d94d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "eth_ibet_wst_tx",
        sa.Column("tx_nonce", sa.BigInteger(), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("eth_ibet_wst_tx", "tx_nonce", schema=get_db_schema())
