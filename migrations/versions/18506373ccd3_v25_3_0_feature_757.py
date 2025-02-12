"""v25_3_0_feature_757

Revision ID: 18506373ccd3
Revises: 02791d34c2ad
Create Date: 2025-02-12 19:10:58.777878

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "18506373ccd3"
down_revision = "02791d34c2ad"
branch_labels = None
depends_on = None


def upgrade():
    #####################################
    # Migration for idx_position
    #####################################
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_position WHERE token_address IS null;")
    )
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_position WHERE account_address IS null;")
    )
    op.get_bind().execute(sa.text(f"DELETE FROM idx_position WHERE modified IS null;"))

    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_position WHERE (modified) NOT IN (
                    SELECT latest_position.max_modified AS modified FROM (
                        SELECT max(modified) AS max_modified FROM idx_position GROUP BY token_address, account_address
                    ) AS latest_position
                );"""
        )
    )
    # nullable => not-nullable
    op.alter_column(
        "idx_position",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    # nullable => not-nullable
    op.alter_column(
        "idx_position",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    # Drop INDEX
    op.drop_index(
        "ix_idx_position_token_address",
        table_name="idx_position",
        schema=get_db_schema(),
    )
    # Drop INDEX
    op.drop_index(
        "ix_idx_position_account_address",
        table_name="idx_position",
        schema=get_db_schema(),
    )
    # Redefine primary key
    op.drop_column("idx_position", "id", schema=get_db_schema())
    op.create_primary_key(
        "idx_position_pkey", "idx_position", ["token_address", "account_address"]
    )

    #####################################
    # Migration for idx_personal_info
    #####################################
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_personal_info WHERE account_address IS null;")
    )
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_personal_info WHERE issuer_address IS null;")
    )
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_personal_info WHERE modified IS null;")
    )

    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_personal_info WHERE (modified) NOT IN (
                    SELECT latest_personal_info.max_modified AS modified FROM (
                        SELECT max(modified) AS max_modified FROM idx_personal_info GROUP BY account_address, issuer_address
                    ) AS latest_personal_info
                );"""
        )
    )
    # nullable => not-nullable
    op.alter_column(
        "idx_personal_info",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    # nullable => not-nullable
    op.alter_column(
        "idx_personal_info",
        "issuer_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    # Drop INDEX
    op.drop_index(
        "ix_idx_personal_info_account_address",
        table_name="idx_personal_info",
        schema=get_db_schema(),
    )
    # Drop INDEX
    op.drop_index(
        "ix_idx_personal_info_issuer_address",
        table_name="idx_personal_info",
        schema=get_db_schema(),
    )
    # Redefine primary key
    op.drop_column("idx_personal_info", "id", schema=get_db_schema())
    op.create_primary_key(
        "idx_personal_info_pkey",
        "idx_personal_info",
        ["account_address", "issuer_address"],
    )


def downgrade():
    op.add_column(
        "idx_position",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_idx_position_token_address",
        "idx_position",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_idx_position_account_address",
        "idx_position",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.add_column(
        "idx_personal_info",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_idx_personal_info_issuer_address",
        "idx_personal_info",
        ["issuer_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_idx_personal_info_account_address",
        "idx_personal_info",
        ["account_address"],
        unique=False,
        schema=get_db_schema(),
    )
