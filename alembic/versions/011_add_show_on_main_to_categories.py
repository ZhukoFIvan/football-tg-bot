"""Add show_on_main to categories

Revision ID: 011
Revises: 010
Create Date: 2025-12-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_label = None
depends_on = None


def upgrade():
    # Добавить поле show_on_main в categories
    op.add_column('categories', sa.Column(
        'show_on_main', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Удалить поле show_on_main
    op.drop_column('categories', 'show_on_main')
