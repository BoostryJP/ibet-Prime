"""v26_6_0_feature_multi_chain_ibet_wst

Revision ID: 5f2c9a8d1e41
Revises: 8607245ba727
Create Date: 2026-04-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "5f2c9a8d1e41"
down_revision = "8607245ba727"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "token",
        sa.Column("ibet_wst_activated_by_blockchain", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_deployed_by_blockchain", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_address_by_blockchain", sa.JSON(), nullable=True),
        schema=get_db_schema(),
    )

    conn = op.get_bind()
    token_table = sa.table(
        "token",
        sa.column("id", sa.Integer),
        sa.column("ibet_wst_activated", sa.Boolean),
        sa.column("ibet_wst_deployed", sa.Boolean),
        sa.column("ibet_wst_address", sa.String),
        sa.column("ibet_wst_activated_by_blockchain", sa.JSON),
        sa.column("ibet_wst_deployed_by_blockchain", sa.JSON),
        sa.column("ibet_wst_address_by_blockchain", sa.JSON),
    )

    rows = conn.execute(
        sa.select(
            token_table.c.id,
            token_table.c.ibet_wst_activated,
            token_table.c.ibet_wst_deployed,
            token_table.c.ibet_wst_address,
        )
    ).mappings()

    for row in rows:
        activated_map = None
        deployed_map = None
        address_map = None

        if row["ibet_wst_activated"] is not None:
            activated_map = {"ethereum": bool(row["ibet_wst_activated"])}
        if row["ibet_wst_deployed"] is not None:
            deployed_map = {"ethereum": bool(row["ibet_wst_deployed"])}
        if row["ibet_wst_address"] is not None:
            address_map = {"ethereum": row["ibet_wst_address"]}

        conn.execute(
            sa.update(token_table)
            .where(token_table.c.id == row["id"])
            .values(
                ibet_wst_activated_by_blockchain=activated_map,
                ibet_wst_deployed_by_blockchain=deployed_map,
                ibet_wst_address_by_blockchain=address_map,
            )
        )

    op.drop_column("token", "ibet_wst_address", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_deployed", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_activated", schema=get_db_schema())


def downgrade():
    op.add_column(
        "token",
        sa.Column("ibet_wst_activated", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_deployed", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token",
        sa.Column("ibet_wst_address", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )

    conn = op.get_bind()
    token_table = sa.table(
        "token",
        sa.column("id", sa.Integer),
        sa.column("ibet_wst_activated", sa.Boolean),
        sa.column("ibet_wst_deployed", sa.Boolean),
        sa.column("ibet_wst_address", sa.String),
        sa.column("ibet_wst_activated_by_blockchain", sa.JSON),
        sa.column("ibet_wst_deployed_by_blockchain", sa.JSON),
        sa.column("ibet_wst_address_by_blockchain", sa.JSON),
    )

    rows = conn.execute(
        sa.select(
            token_table.c.id,
            token_table.c.ibet_wst_activated_by_blockchain,
            token_table.c.ibet_wst_deployed_by_blockchain,
            token_table.c.ibet_wst_address_by_blockchain,
        )
    ).mappings()

    for row in rows:
        activated = None
        deployed = None
        address = None

        activated_map = row["ibet_wst_activated_by_blockchain"] or {}
        deployed_map = row["ibet_wst_deployed_by_blockchain"] or {}
        address_map = row["ibet_wst_address_by_blockchain"] or {}

        if "ethereum" in activated_map:
            activated = bool(activated_map["ethereum"])
        if "ethereum" in deployed_map:
            deployed = bool(deployed_map["ethereum"])
        if "ethereum" in address_map:
            address = address_map["ethereum"]

        conn.execute(
            sa.update(token_table)
            .where(token_table.c.id == row["id"])
            .values(
                ibet_wst_activated=activated,
                ibet_wst_deployed=deployed,
                ibet_wst_address=address,
            )
        )

    op.drop_column("token", "ibet_wst_address_by_blockchain", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_deployed_by_blockchain", schema=get_db_schema())
    op.drop_column("token", "ibet_wst_activated_by_blockchain", schema=get_db_schema())
