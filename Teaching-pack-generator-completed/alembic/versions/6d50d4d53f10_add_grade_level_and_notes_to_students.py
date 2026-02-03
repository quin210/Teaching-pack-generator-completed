"""add_grade_level_and_notes_to_students

Revision ID: 6d50d4d53f10
Revises: 5ba1e24a2c3e
Create Date: 2026-01-10 09:53:45.829292+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d50d4d53f10'
down_revision: Union[str, Sequence[str], None] = '5ba1e24a2c3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add grade_level and notes columns to students table
    op.add_column('students', sa.Column('grade_level', sa.String(50), nullable=True))
    op.add_column('students', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove grade_level and notes columns from students table
    op.drop_column('students', 'notes')
    op.drop_column('students', 'grade_level')
