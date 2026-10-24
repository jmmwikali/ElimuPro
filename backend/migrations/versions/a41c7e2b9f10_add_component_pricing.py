"""add component pricing

Revision ID: a41c7e2b9f10
Revises: 718717373009
Create Date: 2026-10-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a41c7e2b9f10'
down_revision = '718717373009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('price_components',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('billing_unit', sa.String(length=30), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('price_tiers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('component_id', sa.Integer(), nullable=False),
    sa.Column('up_to_students', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['component_id'], ['price_components.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('price_tiers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_price_tiers_component_id'), ['component_id'], unique=False)


def downgrade():
    with op.batch_alter_table('price_tiers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_price_tiers_component_id'))

    op.drop_table('price_tiers')
    op.drop_table('price_components')
