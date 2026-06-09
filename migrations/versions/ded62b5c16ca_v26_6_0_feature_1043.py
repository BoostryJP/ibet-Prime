"""v26_6_0_feature_1043

Revision ID: ded62b5c16ca
Revises: 4ded95375da2
Create Date: 2026-04-20 20:41:12.024932

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "ded62b5c16ca"
down_revision = "4ded95375da2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ibet_wst_whitelist_kyc_delegated_eoa",
        sa.Column("key_manager", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key_manager", "account_address"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("ibet_wst_whitelist_kyc_delegated_eoa", schema=get_db_schema())
