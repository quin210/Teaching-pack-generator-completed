"""Change TeachingPack id to UUID

Revision ID: 90c409c05248
Revises: 9e1e9d12bf92
Create Date: 2026-01-15 11:50:35.830526+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90c409c05248'
down_revision: Union[str, Sequence[str], None] = '9e1e9d12bf92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
