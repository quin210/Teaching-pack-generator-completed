"""add flashcards to lessons

Revision ID: 1a2b3c4d5e6f
Revises: b2e87acf061c
Create Date: 2026-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = 'b2e87acf061c'
branch_labels = None
depends_on = None


def upgrade():
    # Add flashcards column to lessons table
    op.add_column('lessons', sa.Column('flashcards', sa.JSON(), nullable=True))


def downgrade():
    # Remove flashcards column from lessons table
    op.drop_column('lessons', 'flashcards')
