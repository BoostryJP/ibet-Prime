"""v26_6_0_feature_1010

Revision ID: bb4276104a9f
Revises: c2f7c9e8a1b4
Create Date: 2026-04-08 11:58:15.353535

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "bb4276104a9f"
down_revision = "c2f7c9e8a1b4"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "idx_ava_ibet_wst_trade_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_block_data_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_e2e_messaging_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_eth_ibet_wst_trade_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_issue_redeem_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_personal_info_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_position_bond_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_position_share_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_transfer_approval_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_transfer_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holders_list",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holders_list",
        "block_number",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "token_holders_list",
        "block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "token_holders_list",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_transfer_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_transfer_approval_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_position_share_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_position_bond_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_personal_info_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_issue_redeem_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_eth_ibet_wst_trade_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_e2e_messaging_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_block_data_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "idx_ava_ibet_wst_trade_block_number",
        "latest_block_number",
        existing_type=sa.BIGINT(),
        nullable=True,
        schema=get_db_schema(),
    )
