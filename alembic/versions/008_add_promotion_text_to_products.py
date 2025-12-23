"""Add promotion_text to products

Revision ID: 008
Revises: 007
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_label = None
depends_on = None


def upgrade():
    # Добавить promotion_text к products
    op.add_column('products', sa.Column(
        'promotion_text', sa.String(length=200), nullable=True))


def downgrade():
    # Удалить promotion_text
    op.drop_column('products', 'promotion_text')
