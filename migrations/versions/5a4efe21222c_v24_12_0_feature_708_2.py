"""v24_12_0_feature_708_2

Revision ID: 5a4efe21222c
Revises: f7d8342a56ea
Create Date: 2024-11-27 01:45:05.369251

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "5a4efe21222c"
down_revision = "f7d8342a56ea"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ledger_creation_request_data",
        sa.Column("data_source", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column(
        "ledger_creation_request_data", "data_source", schema=get_db_schema()
    )
