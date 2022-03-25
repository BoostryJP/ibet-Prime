"""v22.3.0_feature/#278

Revision ID: f22f8ac0a121
Revises: ec0ac096e294
Create Date: 2022-03-25 18:29:14.846619

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = 'f22f8ac0a121'
down_revision = 'ec0ac096e294'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('upload_file', sa.Column('label', sa.String(length=200), nullable=True), schema=get_db_schema())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('upload_file', 'label', schema=get_db_schema())
    # ### end Alembic commands ###
