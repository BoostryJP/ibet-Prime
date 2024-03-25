"""v23_12_0_feature_562

Revision ID: 679359eceb76
Revises: 380a311952f4
Create Date: 2023-11-25 23:50:48.724937

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update

from app.database import get_db_schema
from app.model.db import Token, TokenVersion

# revision identifiers, used by Alembic.
revision = "679359eceb76"
down_revision = "380a311952f4"
branch_labels = None
depends_on = None


def upgrade():
    # Add column
    op.add_column(
        "token",
        sa.Column("version", sa.String(length=5), nullable=True),
        schema=get_db_schema(),
    )

    # Set default value
    op.get_bind().execute(update(Token).values(version=TokenVersion.V_22_12))

    # Change column to nullable=False
    op.alter_column(
        "token",
        "version",
        existing_type=sa.String(length=5),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("token", "version", schema=get_db_schema())
