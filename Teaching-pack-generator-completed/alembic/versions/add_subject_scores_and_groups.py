"""add subject scores and groups

Revision ID: add_subject_scores
Revises: d5111a331fcb
Create Date: 2026-01-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_subject_scores'
down_revision = 'd5111a331fcb'
branch_labels = None
depends_on = None


def upgrade():
    # Add subject_scores and group_id to students table
    op.add_column('students', sa.Column('subject_scores', sa.JSON(), nullable=True))
    op.add_column('students', sa.Column('group_id', sa.String(50), nullable=True))
    
    # Add groups_configuration to classrooms table
    op.add_column('classrooms', sa.Column('groups_configuration', sa.JSON(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('students', 'group_id')
    op.drop_column('students', 'subject_scores')
    op.drop_column('classrooms', 'groups_configuration')
