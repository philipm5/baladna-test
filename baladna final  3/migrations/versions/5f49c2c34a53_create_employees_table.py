"""Create employees table

Revision ID: 5f49c2c34a53
Revises: 
Create Date: 2024-09-15 13:37:10.357296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f49c2c34a53'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('employees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('monthly_salary', sa.Float(), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('id_number', sa.String(length=50), nullable=False),
    sa.Column('start_date', sa.String(length=10), nullable=False),
    sa.Column('address', sa.String(length=200), nullable=True),
    sa.Column('holidays_taken', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_number')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('employees')
    # ### end Alembic commands ###
