"""add_output_file_path_to_teaching_packs

Revision ID: b6f41b4613c5
Revises: acfa7cf5904b
Create Date: 2026-01-09 09:48:31.243677+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6f41b4613c5'
down_revision: Union[str, Sequence[str], None] = 'acfa7cf5904b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
