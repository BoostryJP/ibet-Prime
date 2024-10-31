"""v24_12_0_feature_700

Revision ID: 68f088d446c4
Revises: 3977b822f983
Create Date: 2024-10-30 10:39:56.378764

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "68f088d446c4"
down_revision = "3977b822f983"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "idx_transfer",
        sa.Column("message", sa.String(length=50), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_transfer_message"),
        "idx_transfer",
        ["message"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_transfer_source_event"),
        "idx_transfer",
        ["source_event"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_idx_transfer_source_event"),
        table_name="idx_transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_transfer_message"),
        table_name="idx_transfer",
        schema=get_db_schema(),
    )
    op.drop_column("idx_transfer", "message", schema=get_db_schema())
