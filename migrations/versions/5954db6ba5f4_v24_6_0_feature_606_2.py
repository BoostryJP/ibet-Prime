"""v24_6_0_feature_606_2

Revision ID: 5954db6ba5f4
Revises: 346d0e814893
Create Date: 2024-04-12 21:45:53.594057

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "5954db6ba5f4"
down_revision = "346d0e814893"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dvp_agent_account",
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
    op.drop_table("dvp_agent_account", schema=get_db_schema())
