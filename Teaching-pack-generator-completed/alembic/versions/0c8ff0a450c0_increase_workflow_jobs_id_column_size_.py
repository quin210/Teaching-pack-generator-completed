"""Increase workflow_jobs.id column size to VARCHAR(100)

Revision ID: 0c8ff0a450c0
Revises: 3ba0ffddfe80
Create Date: 2026-01-21 16:53:59.490426+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c8ff0a450c0'
down_revision: Union[str, Sequence[str], None] = '3ba0ffddfe80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Increase the size of workflow_jobs.id column from VARCHAR(36) to VARCHAR(100)
    op.alter_column('workflow_jobs', 'id',
                    existing_type=sa.String(36),
                    type_=sa.String(100),
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the column size back to VARCHAR(36)
    op.alter_column('workflow_jobs', 'id',
                    existing_type=sa.String(100),
                    type_=sa.String(36),
                    existing_nullable=False)
