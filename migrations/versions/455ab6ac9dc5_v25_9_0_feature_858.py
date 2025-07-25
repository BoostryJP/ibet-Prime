"""v25_9_0_feature_858

Revision ID: 455ab6ac9dc5
Revises: cfb5c6ce3197
Create Date: 2025-07-25 18:59:06.853816

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update, cast, String

from app.database import get_db_schema
from app.model.db import IDXTransfer, IDXLock, IDXUnlock

# revision identifiers, used by Alembic.
revision = "455ab6ac9dc5"
down_revision = "cfb5c6ce3197"
branch_labels = None
depends_on = None


def upgrade():
    # ### end Alembic commands ###
    op.get_bind().execute(
        update(IDXTransfer)
        .values(message=None, data={})
        .where(IDXTransfer.message == "inheritance")
    )
    op.get_bind().execute(
        update(IDXLock)
        .values(data={})
        .where(cast(IDXLock.data, String).like(f"%inheritance%"))
    )
    op.get_bind().execute(
        update(IDXUnlock)
        .values(data={})
        .where(cast(IDXUnlock.data, String).like(f"%inheritance%"))
    )


def downgrade():
    pass
