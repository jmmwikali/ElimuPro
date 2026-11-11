"""add platform modules, leadership and careergps

Revision ID: a1b2c3d4e5f6
Revises: f5b7d2a91c38
Create Date: 2026-11-11 08:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f5b7d2a91c38'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('platform_modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_core', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('school_modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('module_code', sa.String(length=40), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('enabled_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school_id', 'module_code')
    )
    op.create_index(op.f('ix_school_modules_school_id'), 'school_modules', ['school_id'], unique=False)
    op.create_index(op.f('ix_school_modules_module_code'), 'school_modules', ['module_code'], unique=False)

    op.create_table('leadership_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('designation', sa.String(length=120), nullable=False),
        sa.Column('acknowledgement', sa.Text(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('career_paths',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=80), nullable=True),
        sa.Column('related_subjects', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_career_paths_school_id'), 'career_paths', ['school_id'], unique=False)

    op.create_table('student_career_interests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('career_path_id', sa.Integer(), nullable=False),
        sa.Column('interest_level', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['career_path_id'], ['career_paths.id'], ),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_student_career_interests_school_id'), 'student_career_interests', ['school_id'], unique=False)
    op.create_index(op.f('ix_student_career_interests_student_id'), 'student_career_interests', ['student_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_student_career_interests_student_id'), table_name='student_career_interests')
    op.drop_index(op.f('ix_student_career_interests_school_id'), table_name='student_career_interests')
    op.drop_table('student_career_interests')
    op.drop_index(op.f('ix_career_paths_school_id'), table_name='career_paths')
    op.drop_table('career_paths')
    op.drop_table('leadership_profiles')
    op.drop_index(op.f('ix_school_modules_module_code'), table_name='school_modules')
    op.drop_index(op.f('ix_school_modules_school_id'), table_name='school_modules')
    op.drop_table('school_modules')
    op.drop_table('platform_modules')
