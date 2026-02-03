"""add theory questions to lessons

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b3c4d5e6f7a'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    # Add theory_questions column to lessons table
    op.add_column('lessons', sa.Column('theory_questions', sa.JSON(), nullable=True))


def downgrade():
    # Remove theory_questions column from lessons table
    op.drop_column('lessons', 'theory_questions')
