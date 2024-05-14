"""v24_6_0_feature_627

Revision ID: 0656c408ebbb
Revises: 5954db6ba5f4
Create Date: 2024-05-14 09:40:35.862686

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "0656c408ebbb"
down_revision = "5954db6ba5f4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idx_personal_info_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=True),
        sa.Column("issuer_address", sa.String(length=42), nullable=True),
        sa.Column("event_type", sa.String(length=10), nullable=False),
        sa.Column("personal_info", sa.JSON(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_personal_info_history_account_address"),
        "idx_personal_info_history",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_personal_info_history_event_type"),
        "idx_personal_info_history",
        ["event_type"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_idx_personal_info_history_issuer_address"),
        "idx_personal_info_history",
        ["issuer_address"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_idx_personal_info_history_issuer_address"),
        table_name="idx_personal_info_history",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_personal_info_history_event_type"),
        table_name="idx_personal_info_history",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_idx_personal_info_history_account_address"),
        table_name="idx_personal_info_history",
        schema=get_db_schema(),
    )
    op.drop_table("idx_personal_info_history", schema=get_db_schema())
