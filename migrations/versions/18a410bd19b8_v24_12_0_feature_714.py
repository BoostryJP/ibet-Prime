"""v24_12_0_feature_714

Revision ID: 18a410bd19b8
Revises: 68f088d446c4
Create Date: 2024-11-06 17:51:28.968429

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "18a410bd19b8"
down_revision = "68f088d446c4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tmp_batch_create_child_account",
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("child_account_index", sa.BigInteger(), nullable=False),
        sa.Column("personal_info", sa.JSON(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("issuer_address", "child_account_index"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("tmp_batch_create_child_account", schema=get_db_schema())
