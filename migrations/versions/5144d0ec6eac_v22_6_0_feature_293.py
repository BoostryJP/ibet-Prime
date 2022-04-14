"""v22_6_0_feature_293

Revision ID: 5144d0ec6eac
Revises: f22f8ac0a121
Create Date: 2022-04-13 11:40:48.985574

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = '5144d0ec6eac'
down_revision = 'f22f8ac0a121'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('idx_transfer_approval', sa.Column('escrow_finished', sa.Boolean(), nullable=True), schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('idx_transfer_approval', 'escrow_finished', schema=get_db_schema())
    # ### end Alembic commands ###
