"""v23_12_0_feature_546

Revision ID: 53caec5f4dce
Revises: 8ed94523e21c
Create Date: 2023-10-30 21:35:34.922094

"""
from alembic import op
from sqlalchemy import delete

from app.model.db import TokenCache

# revision identifiers, used by Alembic.
revision = "53caec5f4dce"
down_revision = "8ed94523e21c"
branch_labels = None
depends_on = None


def upgrade():
    # Delete all `token_cache` data
    op.get_bind().execute(delete(TokenCache))


def downgrade():
    pass
