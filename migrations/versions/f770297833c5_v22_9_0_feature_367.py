"""v22.9.0_feature_367

Revision ID: f770297833c5
Revises: 47bf57b85b0a
Create Date: 2022-08-09 19:02:19.545853

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = 'f770297833c5'
down_revision = '47bf57b85b0a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('batch_issue_redeem', 'amount',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False, schema=get_db_schema())
    op.alter_column('bulk_transfer', 'amount',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'amount',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'balance',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'price',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('utxo', 'amount',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True, schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('utxo', 'amount',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'price',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'balance',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('ledger_details_data', 'amount',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True, schema=get_db_schema())
    op.alter_column('bulk_transfer', 'amount',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False, schema=get_db_schema())
    op.alter_column('batch_issue_redeem', 'amount',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False, schema=get_db_schema())
    # ### end Alembic commands ###
