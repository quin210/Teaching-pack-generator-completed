"""drop_groups_column_from_teaching_packs

Revision ID: 15612ed2bf17
Revises: 94b40c00441a
Create Date: 2026-01-15 12:02:19.614923+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15612ed2bf17'
down_revision: Union[str, Sequence[str], None] = '94b40c00441a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('teaching_packs')]
    if 'groups' in columns:
        op.drop_column('teaching_packs', 'groups')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the groups column
    op.add_column('teaching_packs', sa.Column('groups', sa.JSON(), nullable=True))
