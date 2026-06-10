"""wipe_legacy_data_and_remove_max_scenes

Revision ID: 2c1ca0370dce
Revises: 001_initial
Create Date: 2026-05-14 16:05:57.084296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c1ca0370dce'
down_revision: Union[str, Sequence[str], None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Wipe legacy data
    op.execute("DELETE FROM scenes")
    op.execute("DELETE FROM jobs")
    op.execute("DELETE FROM videos")

    # Remove max_scenes column from jobs table
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('max_scenes')

    # Add infinite-canvas spatial columns to scenes table
    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('canvas_x', sa.INTEGER(), server_default=sa.text('0'), nullable=False))
        batch_op.add_column(sa.Column('canvas_y', sa.INTEGER(), server_default=sa.text('0'), nullable=False))
        batch_op.add_column(sa.Column('canvas_width', sa.INTEGER(), server_default=sa.text('1920'), nullable=False))
        batch_op.add_column(sa.Column('canvas_height', sa.INTEGER(), server_default=sa.text('1080'), nullable=False))
        batch_op.add_column(sa.Column('layout_direction', sa.String(32), server_default='right', nullable=False))
        batch_op.add_column(sa.Column('kinetic_words_json', sa.Text(), server_default='[]', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.drop_column('kinetic_words_json')
        batch_op.drop_column('layout_direction')
        batch_op.drop_column('canvas_height')
        batch_op.drop_column('canvas_width')
        batch_op.drop_column('canvas_y')
        batch_op.drop_column('canvas_x')

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_scenes', sa.INTEGER(), server_default=sa.text('15'), nullable=False))
