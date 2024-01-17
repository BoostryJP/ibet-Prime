"""v24.3.0_feature_582

Revision ID: 6814beab6ff6
Revises: beb9a0e876f8
Create Date: 2024-01-17 16:54:14.187273

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "6814beab6ff6"
down_revision = "beb9a0e876f8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "freeze_log_account",
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("keyfile", sa.JSON(), nullable=True),
        sa.Column("eoa_password", sa.String(length=2000), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("account_address"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("freeze_log_account", schema=get_db_schema())
