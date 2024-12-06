"""v24_12_0_feature_723

Revision ID: 3b7e17706e3e
Revises: 5a4efe21222c
Create Date: 2024-12-06 21:21:44.983618

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "3b7e17706e3e"
down_revision = "5a4efe21222c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_holder_extra_info",
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("external_id_1_type", sa.String(length=50), nullable=True),
        sa.Column("external_id_1", sa.String(length=50), nullable=True),
        sa.Column("external_id_2_type", sa.String(length=50), nullable=True),
        sa.Column("external_id_2", sa.String(length=50), nullable=True),
        sa.Column("external_id_3_type", sa.String(length=50), nullable=True),
        sa.Column("external_id_3", sa.String(length=50), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("token_address", "account_address"),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_table("token_holder_extra_info", schema=get_db_schema())
