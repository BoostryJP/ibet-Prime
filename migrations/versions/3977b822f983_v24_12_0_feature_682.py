"""v24_12_0_feature_682

Revision ID: 3977b822f983
Revises: f728fd994b80
Create Date: 2024-09-28 01:10:07.686046

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update

from app.database import get_db_schema
from app.model.db import IDXPersonalInfo, PersonalInfoDataSource

# revision identifiers, used by Alembic.
revision = "3977b822f983"
down_revision = "f728fd994b80"
branch_labels = None
depends_on = None


def upgrade():
    # Create TBL - ChildAccountIndex
    op.create_table(
        "child_account_index",
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("latest_index", sa.BigInteger(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("issuer_address"),
        schema=get_db_schema(),
    )

    # Create TBL - ChildAccount
    op.create_table(
        "child_account",
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("child_account_index", sa.BigInteger(), nullable=False),
        sa.Column("child_account_address", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("issuer_address", "child_account_index"),
        schema=get_db_schema(),
    )

    # Add column - Account
    op.add_column(
        "account",
        sa.Column("issuer_public_key", sa.String(length=66), nullable=True),
        schema=get_db_schema(),
    )

    # Add column - IDXPersonalInfo
    op.add_column(
        "idx_personal_info",
        sa.Column("data_source", sa.String(length=10), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(
        update(IDXPersonalInfo).values(data_source=PersonalInfoDataSource.ON_CHAIN)
    )
    op.alter_column(
        "idx_personal_info",
        "data_source",
        existing_type=sa.String(length=10),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("idx_personal_info", "data_source", schema=get_db_schema())
    op.drop_column("account", "issuer_public_key", schema=get_db_schema())
    op.drop_table("child_account_index", schema=get_db_schema())
    op.drop_table("child_account", schema=get_db_schema())
