"""merge heads

Revision ID: 5ba1e24a2c3e
Revises: add_subject_scores, c0ab1f3702cc
Create Date: 2026-01-10 09:10:23.279229+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ba1e24a2c3e'
down_revision: Union[str, Sequence[str], None] = ('add_subject_scores', 'c0ab1f3702cc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
