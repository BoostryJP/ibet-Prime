"""v21_12_0_feature_432

Revision ID: ff1d28df9f37
Revises: 1dddc4e2d4e6
Create Date: 2022-12-08 21:46:44.906723

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = 'ff1d28df9f37'
down_revision = '1dddc4e2d4e6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('block_data',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('modified', sa.DateTime(), nullable=True),
    sa.Column('number', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('parent_hash', sa.String(length=66), nullable=False),
    sa.Column('sha3_uncles', sa.String(length=66), nullable=True),
    sa.Column('miner', sa.String(length=42), nullable=True),
    sa.Column('state_root', sa.String(length=66), nullable=True),
    sa.Column('transactions_root', sa.String(length=66), nullable=True),
    sa.Column('receipts_root', sa.String(length=66), nullable=True),
    sa.Column('logs_bloom', sa.String(length=514), nullable=True),
    sa.Column('difficulty', sa.BigInteger(), nullable=True),
    sa.Column('gas_limit', sa.Integer(), nullable=True),
    sa.Column('gas_used', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.Integer(), nullable=False),
    sa.Column('proof_of_authority_data', sa.Text(), nullable=True),
    sa.Column('mix_hash', sa.String(length=66), nullable=True),
    sa.Column('nonce', sa.String(length=18), nullable=True),
    sa.Column('hash', sa.String(length=66), nullable=False),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.Column('transactions', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('number')
    , schema=get_db_schema())
    op.create_index(op.f('ix_block_data_hash'), 'block_data', ['hash'], unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_block_data_timestamp'), 'block_data', ['timestamp'], unique=False, schema=get_db_schema())
    op.create_table('idx_block_data_block_number',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('modified', sa.DateTime(), nullable=True),
    sa.Column('chain_id', sa.String(length=10), nullable=False),
    sa.Column('latest_block_number', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('chain_id')
    , schema=get_db_schema())
    op.create_table('tx_data',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('modified', sa.DateTime(), nullable=True),
    sa.Column('hash', sa.String(length=66), nullable=False),
    sa.Column('block_hash', sa.String(length=66), nullable=True),
    sa.Column('block_number', sa.BigInteger(), nullable=True),
    sa.Column('transaction_index', sa.Integer(), nullable=True),
    sa.Column('from_address', sa.String(length=42), nullable=True),
    sa.Column('to_address', sa.String(length=42), nullable=True),
    sa.Column('input', sa.Text(), nullable=True),
    sa.Column('gas', sa.Integer(), nullable=True),
    sa.Column('gas_price', sa.BigInteger(), nullable=True),
    sa.Column('value', sa.BigInteger(), nullable=True),
    sa.Column('nonce', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('hash')
    , schema=get_db_schema())
    op.create_index(op.f('ix_tx_data_block_number'), 'tx_data', ['block_number'], unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_tx_data_from_address'), 'tx_data', ['from_address'], unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_tx_data_to_address'), 'tx_data', ['to_address'], unique=False, schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_tx_data_to_address'), table_name='tx_data', schema=get_db_schema())
    op.drop_index(op.f('ix_tx_data_from_address'), table_name='tx_data', schema=get_db_schema())
    op.drop_index(op.f('ix_tx_data_block_number'), table_name='tx_data', schema=get_db_schema())
    op.drop_table('tx_data', schema=get_db_schema())
    op.drop_table('idx_block_data_block_number', schema=get_db_schema())
    op.drop_index(op.f('ix_block_data_timestamp'), table_name='block_data', schema=get_db_schema())
    op.drop_index(op.f('ix_block_data_hash'), table_name='block_data', schema=get_db_schema())
    op.drop_table('block_data', schema=get_db_schema())
    # ### end Alembic commands ###
