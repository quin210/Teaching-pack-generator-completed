"""add_output_file_path_to_teaching_packs

Revision ID: 2cadae36416a
Revises: b6f41b4613c5
Create Date: 2026-01-09 09:48:36.977301+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cadae36416a'
down_revision: Union[str, Sequence[str], None] = 'b6f41b4613c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add output_file_path column to teaching_packs table
    op.add_column('teaching_packs', sa.Column('output_file_path', sa.String(500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove output_file_path column from teaching_packs table
    op.drop_column('teaching_packs', 'output_file_path')
