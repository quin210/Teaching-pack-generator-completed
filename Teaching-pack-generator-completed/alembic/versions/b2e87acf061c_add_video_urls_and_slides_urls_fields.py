"""add_video_urls_and_slides_urls_fields

Revision ID: b2e87acf061c
Revises: 15612ed2bf17
Create Date: 2026-01-15 13:46:31.163698+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2e87acf061c'
down_revision: Union[str, Sequence[str], None] = '15612ed2bf17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add video_urls and slides_urls columns to teaching_packs table
    op.add_column('teaching_packs', sa.Column('video_urls', sa.JSON(), nullable=True))
    op.add_column('teaching_packs', sa.Column('slides_urls', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove video_urls and slides_urls columns from teaching_packs table
    op.drop_column('teaching_packs', 'video_urls')
    op.drop_column('teaching_packs', 'slides_urls')
