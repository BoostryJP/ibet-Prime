"""v0.0.1

Revision ID: eb598f89de10
Revises: 
Create Date: 2021-03-16 18:56:54.674264

"""
from alembic import op
import sqlalchemy as sa

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = 'eb598f89de10'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('account',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('issuer_address', sa.String(length=42), nullable=False),
                    sa.Column('keyfile', sa.JSON(), nullable=True),
                    sa.Column('eoa_password', sa.String(length=2000), nullable=True),
                    sa.Column('rsa_private_key', sa.String(length=8000), nullable=True),
                    sa.Column('rsa_public_key', sa.String(length=2000), nullable=True),
                    sa.Column('rsa_passphrase', sa.String(length=2000), nullable=True),
                    sa.Column('rsa_status', sa.Integer(), nullable=True),
                    sa.PrimaryKeyConstraint('issuer_address')
                    , schema=get_db_schema())
    op.create_table('account_rsa_key_temporary',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('issuer_address', sa.String(length=42), nullable=False),
                    sa.Column('rsa_private_key', sa.String(length=8000), nullable=True),
                    sa.Column('rsa_public_key', sa.String(length=2000), nullable=True),
                    sa.Column('rsa_passphrase', sa.String(length=2000), nullable=True),
                    sa.PrimaryKeyConstraint('issuer_address')
                    , schema=get_db_schema())
    op.create_table('bulk_transfer',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('issuer_address', sa.String(length=42), nullable=False),
                    sa.Column('upload_id', sa.String(length=36), nullable=True),
                    sa.Column('token_address', sa.String(length=42), nullable=False),
                    sa.Column('token_type', sa.String(length=40), nullable=False),
                    sa.Column('from_address', sa.String(length=42), nullable=False),
                    sa.Column('to_address', sa.String(length=42), nullable=False),
                    sa.Column('amount', sa.Integer(), nullable=False),
                    sa.Column('status', sa.Integer(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_index(op.f('ix_bulk_transfer_issuer_address'), 'bulk_transfer', ['issuer_address'], unique=False,
                    schema=get_db_schema())
    op.create_index(op.f('ix_bulk_transfer_status'), 'bulk_transfer', ['status'], unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_bulk_transfer_upload_id'), 'bulk_transfer', ['upload_id'], unique=False,
                    schema=get_db_schema())
    op.create_table('bulk_transfer_upload',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('upload_id', sa.String(length=36), nullable=False),
                    sa.Column('issuer_address', sa.String(length=42), nullable=False),
                    sa.Column('status', sa.Integer(), nullable=False),
                    sa.PrimaryKeyConstraint('upload_id')
                    , schema=get_db_schema())
    op.create_index(op.f('ix_bulk_transfer_upload_issuer_address'), 'bulk_transfer_upload', ['issuer_address'],
                    unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_bulk_transfer_upload_status'), 'bulk_transfer_upload', ['status'], unique=False,
                    schema=get_db_schema())
    op.create_table('idx_personal_info',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
                    sa.Column('account_address', sa.String(length=42), nullable=True),
                    sa.Column('issuer_address', sa.String(length=42), nullable=True),
                    sa.Column('personal_info', sa.JSON(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_index(op.f('ix_idx_personal_info_account_address'), 'idx_personal_info', ['account_address'],
                    unique=False, schema=get_db_schema())
    op.create_index(op.f('ix_idx_personal_info_issuer_address'), 'idx_personal_info', ['issuer_address'], unique=False,
                    schema=get_db_schema())
    op.create_table('idx_personal_info_block_number',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
                    sa.Column('latest_block_number', sa.BigInteger(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_table('idx_position',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
                    sa.Column('token_address', sa.String(length=42), nullable=True),
                    sa.Column('account_address', sa.String(length=42), nullable=True),
                    sa.Column('balance', sa.BigInteger(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_index(op.f('ix_idx_position_account_address'), 'idx_position', ['account_address'], unique=False,
                    schema=get_db_schema())
    op.create_index(op.f('ix_idx_position_token_address'), 'idx_position', ['token_address'], unique=False,
                    schema=get_db_schema())
    op.create_table('idx_transfer',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
                    sa.Column('transaction_hash', sa.String(length=66), nullable=True),
                    sa.Column('token_address', sa.String(length=42), nullable=True),
                    sa.Column('transfer_from', sa.String(length=42), nullable=True),
                    sa.Column('transfer_to', sa.String(length=42), nullable=True),
                    sa.Column('amount', sa.BigInteger(), nullable=True),
                    sa.Column('block_timestamp', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_token_address'), 'idx_transfer', ['token_address'], unique=False,
                    schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_transaction_hash'), 'idx_transfer', ['transaction_hash'], unique=False,
                    schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_transfer_from'), 'idx_transfer', ['transfer_from'], unique=False,
                    schema=get_db_schema())
    op.create_index(op.f('ix_idx_transfer_transfer_to'), 'idx_transfer', ['transfer_to'], unique=False,
                    schema=get_db_schema())
    op.create_table('token',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('type', sa.String(length=40), nullable=False),
                    sa.Column('tx_hash', sa.String(length=66), nullable=False),
                    sa.Column('issuer_address', sa.String(length=42), nullable=True),
                    sa.Column('token_address', sa.String(length=42), nullable=True),
                    sa.Column('abi', sa.JSON(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    , schema=get_db_schema())
    op.create_table('tx_management',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('tx_from', sa.String(length=42), nullable=False),
                    sa.PrimaryKeyConstraint('tx_from')
                    , schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('tx_management', schema=get_db_schema())
    op.drop_table('token', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_transfer_to'), table_name='idx_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_transfer_from'), table_name='idx_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_transaction_hash'), table_name='idx_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_transfer_token_address'), table_name='idx_transfer', schema=get_db_schema())
    op.drop_table('idx_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_position_token_address'), table_name='idx_position', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_position_account_address'), table_name='idx_position', schema=get_db_schema())
    op.drop_table('idx_position', schema=get_db_schema())
    op.drop_table('idx_personal_info_block_number', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_personal_info_issuer_address'), table_name='idx_personal_info', schema=get_db_schema())
    op.drop_index(op.f('ix_idx_personal_info_account_address'), table_name='idx_personal_info', schema=get_db_schema())
    op.drop_table('idx_personal_info', schema=get_db_schema())
    op.drop_index(op.f('ix_bulk_transfer_upload_status'), table_name='bulk_transfer_upload', schema=get_db_schema())
    op.drop_index(op.f('ix_bulk_transfer_upload_issuer_address'), table_name='bulk_transfer_upload',
                  schema=get_db_schema())
    op.drop_table('bulk_transfer_upload', schema=get_db_schema())
    op.drop_index(op.f('ix_bulk_transfer_upload_id'), table_name='bulk_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_bulk_transfer_status'), table_name='bulk_transfer', schema=get_db_schema())
    op.drop_index(op.f('ix_bulk_transfer_issuer_address'), table_name='bulk_transfer', schema=get_db_schema())
    op.drop_table('bulk_transfer', schema=get_db_schema())
    op.drop_table('account_rsa_key_temporary', schema=get_db_schema())
    op.drop_table('account', schema=get_db_schema())
    # ### end Alembic commands ###