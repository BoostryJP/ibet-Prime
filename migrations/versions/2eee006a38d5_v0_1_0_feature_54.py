"""v0.1.0_feature_54

Revision ID: 2eee006a38d5
Revises: fe0437ec5e6d
Create Date: 2021-04-08 20:24:22.465013

"""
import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "2eee006a38d5"
down_revision = "fe0437ec5e6d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "scheduled_events",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("issuer_address", sa.String(length=42), nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("token_type", sa.String(length=40), nullable=False),
        sa.Column("scheduled_datetime", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_scheduled_events_status"),
        "scheduled_events",
        ["status"],
        unique=False,
        schema=get_db_schema(),
    )
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column("ledger_admin_headquarters", sa.String(length=200), nullable=False),
        schema=get_db_schema(),
    )
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column("ledger_admin_name", sa.String(length=200), nullable=False),
        schema=get_db_schema(),
    )
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column("ledger_admin_office_address", sa.String(length=200), nullable=False),
        schema=get_db_schema(),
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn", "hq_address", schema=get_db_schema()
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn", "hq_name", schema=get_db_schema()
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn",
        "hq_office_address",
        schema=get_db_schema(),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column(
            "hq_office_address",
            sa.VARCHAR(length=200),
            autoincrement=False,
            nullable=False,
        ),
        schema=get_db_schema(),
    )
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column(
            "hq_name", sa.VARCHAR(length=200), autoincrement=False, nullable=False
        ),
        schema=get_db_schema(),
    )
    op.add_column(
        "corporate_bond_ledger_template_jpn",
        sa.Column(
            "hq_address", sa.VARCHAR(length=200), autoincrement=False, nullable=False
        ),
        schema=get_db_schema(),
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn",
        "ledger_admin_office_address",
        schema=get_db_schema(),
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn",
        "ledger_admin_name",
        schema=get_db_schema(),
    )
    op.drop_column(
        "corporate_bond_ledger_template_jpn",
        "ledger_admin_headquarters",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_scheduled_events_status"),
        table_name="scheduled_events",
        schema=get_db_schema(),
    )
    op.drop_table("scheduled_events", schema=get_db_schema())
    # ### end Alembic commands ###
