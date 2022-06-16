"""v22_6_0_feature_309

Revision ID: 7fe46c2af01e
Revises: 5144d0ec6eac
Create Date: 2022-05-09 17:56:44.525807

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = '7fe46c2af01e'
down_revision = '5144d0ec6eac'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('token_holder',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('modified', sa.DateTime(), nullable=True),
    sa.Column('holder_list_id', sa.BigInteger(), nullable=False),
    sa.Column('account_address', sa.String(length=42), nullable=False),
    sa.Column('hold_balance', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('holder_list_id', 'account_address')
    , schema=get_db_schema())
    op.create_table('token_holders_list',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('modified', sa.DateTime(), nullable=True),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('token_address', sa.String(length=42), nullable=True),
    sa.Column('block_number', sa.BigInteger(), nullable=True),
    sa.Column('list_id', sa.String(length=36), nullable=True),
    sa.Column('batch_status', sa.String(length=256), nullable=True),
    sa.PrimaryKeyConstraint('id')
    , schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('token_holders_list', schema=get_db_schema())
    op.drop_table('token_holder', schema=get_db_schema())
    # ### end Alembic commands ###