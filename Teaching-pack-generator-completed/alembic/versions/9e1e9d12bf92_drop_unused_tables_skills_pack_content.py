"""drop_unused_tables_skills_pack_content

Revision ID: 9e1e9d12bf92
Revises: 0736fa9cfd4d
Create Date: 2026-01-15 08:52:08.663635+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e1e9d12bf92'
down_revision: Union[str, Sequence[str], None] = '0736fa9cfd4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop unused tables if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'teaching_pack_skills' in existing_tables:
        op.drop_table('teaching_pack_skills')
    if 'group_pack_content' in existing_tables:
        op.drop_table('group_pack_content')
    if 'skills' in existing_tables:
        op.drop_table('skills')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate tables if needed (optional)
    pass
