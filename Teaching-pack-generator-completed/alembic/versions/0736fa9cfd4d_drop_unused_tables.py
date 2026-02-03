"""drop_unused_tables

Revision ID: 0736fa9cfd4d
Revises: ac4c06cb8a5d
Create Date: 2026-01-15 08:44:32.941999+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0736fa9cfd4d'
down_revision: Union[str, Sequence[str], None] = 'ac4c06cb8a5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Drop unused tables."""
    # Drop tables that are no longer used
    op.drop_table('group_pack_content')
    op.drop_table('teaching_pack_skills')
    op.drop_table('teaching_groups')
    op.drop_table('diagnostic_results')
    op.drop_table('diagnostic_questions')
    op.drop_table('skills')


def downgrade() -> None:
    """Downgrade schema - Recreate dropped tables."""
    # Recreate skills table
    op.create_table('skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.String(length=50), nullable=False),
        sa.Column('difficulty_level', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('skill_id')
    )
    op.create_index(op.f('ix_skills_id'), 'skills', ['id'], unique=False)
    
    # Recreate other tables if needed (simplified for now)
