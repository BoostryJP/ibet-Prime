"""v0.1.0_feature/#157

Revision ID: f6056503a291
Revises: 0d4133a5b0e3
Create Date: 2021-06-23 16:00:23.143197

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema, engine

# revision identifiers, used by Alembic.
revision = 'f6056503a291'
down_revision = '0d4133a5b0e3'
branch_labels = None
depends_on = None


def upgrade():
    """
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('idx_transfer', sa.Column('from_address', sa.String(length=42), nullable=True), schema=get_db_schema())
    op.add_column('idx_transfer', sa.Column('to_address', sa.String(length=42), nullable=True), schema=get_db_schema())
    op.drop_index('ix_idx_transfer_transfer_from', table_name='idx_transfer', schema=get_db_schema())
    op.drop_index('ix_idx_transfer_transfer_to', table_name='idx_transfer', schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_from_address'), 'idx_transfer', ['from_address'], unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_to_address'), 'idx_transfer', ['to_address'], unique=False, schema=get_db_schema())
    op.drop_column('idx_transfer', 'transfer_from', schema=get_db_schema())
    op.drop_column('idx_transfer', 'transfer_to', schema=get_db_schema())
    # ### end Alembic commands ###
    """
    op.alter_column('idx_transfer', 'transfer_from', new_column_name='from_address', existing_type=sa.String(length=42), schema=get_db_schema())
    op.alter_column('idx_transfer', 'transfer_to', new_column_name='to_address', existing_type=sa.String(length=42), schema=get_db_schema())
    if engine.name == "postgresql":
        schema = get_db_schema()
        schema = f"{schema}." if schema is not None else ""
        op.execute(f"ALTER INDEX {schema}ix_idx_transfer_transfer_from RENAME TO ix_idx_transfer_from_address")
        op.execute(f"ALTER INDEX {schema}ix_idx_transfer_transfer_to RENAME TO ix_idx_transfer_from_to")
    elif engine.name == "mysql":
        op.execute("ALTER TABLE idx_transfer RENAME INDEX ix_idx_transfer_transfer_from TO ix_idx_transfer_from_address")
        op.execute("ALTER TABLE idx_transfer RENAME INDEX ix_idx_transfer_transfer_to TO ix_idx_transfer_to_address")


def downgrade():
    """
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('idx_transfer', sa.Column('transfer_to', sa.VARCHAR(length=42), autoincrement=False, nullable=True), schema=get_db_schema())
    op.add_column('idx_transfer', sa.Column('transfer_from', sa.VARCHAR(length=42), autoincrement=False, nullable=True), schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_to_address'), table_name='idx_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_from_address'), table_name='idx_transfer', schema=get_db_schema())
    op.create_index('ix_idx_transfer_transfer_to', 'idx_transfer', ['transfer_to'], unique=False, schema=get_db_schema())
    op.create_index('ix_idx_transfer_transfer_from', 'idx_transfer', ['transfer_from'], unique=False, schema=get_db_schema())
    op.drop_column('idx_transfer', 'to_address', schema=get_db_schema())
    op.drop_column('idx_transfer', 'from_address', schema=get_db_schema())
    # ### end Alembic commands ###
    """
    op.alter_column('idx_transfer', 'from_address', new_column_name='transfer_from', existing_type=sa.String(length=42), schema=get_db_schema())
    op.alter_column('idx_transfer', 'to_address', new_column_name='transfer_to', existing_type=sa.String(length=42), schema=get_db_schema())
    if engine.name == "postgresql":
        schema = get_db_schema()
        schema = f"{schema}." if schema is not None else ""
        op.execute(f"ALTER INDEX {schema}ix_idx_transfer_from_address RENAME TO ix_idx_transfer_transfer_from")
        op.execute(f"ALTER INDEX {schema}ix_idx_transfer_from_to RENAME TO ix_idx_transfer_transfer_to")
    elif engine.name == "mysql":
        op.execute("ALTER TABLE idx_transfer RENAME INDEX ix_idx_transfer_transfer_from TO ix_idx_transfer_from_address")
        op.execute("ALTER TABLE idx_transfer RENAME INDEX ix_idx_transfer_transfer_to TO ix_idx_transfer_to_address")
