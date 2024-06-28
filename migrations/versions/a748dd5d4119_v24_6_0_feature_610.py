"""v24_6_0_feature_610

Revision ID: a748dd5d4119
Revises: cb24da38646e
Create Date: 2024-04-07 00:40:00.047349

"""

from alembic import op
from sqlalchemy import delete

from app.model.db import TokenCache

# revision identifiers, used by Alembic.
revision = "a748dd5d4119"
down_revision = "cb24da38646e"
branch_labels = None
depends_on = None


def upgrade():
    # Delete all `token_cache` data
    op.get_bind().execute(delete(TokenCache))


def downgrade():
    pass
