"""Change rest_time to end_time in sections

Revision ID: 006
Revises: 005
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_label = None
depends_on = None


def upgrade():
    # Удалить rest_time
    op.drop_column('sections', 'rest_time')

    # Добавить end_time
    op.add_column('sections', sa.Column(
        'end_time', sa.DateTime(), nullable=True))


def downgrade():
    # Удалить end_time
    op.drop_column('sections', 'end_time')

    # Вернуть rest_time
    op.add_column('sections', sa.Column(
        'rest_time', sa.Integer(), nullable=True))
