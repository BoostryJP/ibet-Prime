"""v26_6_0_feature_1011

Revision ID: 301b31d8c870
Revises: bb4276104a9f
Create Date: 2026-04-08 21:43:03.115919

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "301b31d8c870"
down_revision = "bb4276104a9f"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "e2e_messaging_account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "rsa_key_generate_interval",
        existing_type=sa.INTEGER(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "rsa_generation",
        existing_type=sa.INTEGER(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "transaction_hash",
        existing_type=sa.VARCHAR(length=66),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_private_key",
        existing_type=sa.VARCHAR(length=4000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_public_key",
        existing_type=sa.VARCHAR(length=1000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_passphrase",
        existing_type=sa.VARCHAR(length=2000),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "block_timestamp",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "update_token",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "update_token",
        "issuer_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "update_token",
        "issuer_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "update_token",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "block_timestamp",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_passphrase",
        existing_type=sa.VARCHAR(length=2000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_public_key",
        existing_type=sa.VARCHAR(length=1000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "rsa_private_key",
        existing_type=sa.VARCHAR(length=4000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account_rsa_key",
        "transaction_hash",
        existing_type=sa.VARCHAR(length=66),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "rsa_generation",
        existing_type=sa.INTEGER(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "rsa_key_generate_interval",
        existing_type=sa.INTEGER(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "eoa_password",
        existing_type=sa.VARCHAR(length=2000),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "e2e_messaging_account",
        "keyfile",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        schema=get_db_schema(),
    )
