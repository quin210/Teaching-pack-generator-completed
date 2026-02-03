"""drop_teaching_groups_table

Revision ID: 94b40c00441a
Revises: 90c409c05248
Create Date: 2026-01-15 11:53:13.867198+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94b40c00441a'
down_revision: Union[str, Sequence[str], None] = '90c409c05248'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the teaching_groups table as data is now stored in JSON
    op.drop_table('teaching_groups')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the teaching_groups table
    op.create_table('teaching_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teaching_pack_id', sa.Integer(), nullable=False),
        sa.Column('group_name', sa.String(length=255), nullable=False),
        sa.Column('focus_area', sa.String(length=500), nullable=True),
        sa.Column('mastery_level', sa.String(length=50), nullable=True),
        sa.Column('student_ids', sa.JSON(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['teaching_pack_id'], ['teaching_packs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
