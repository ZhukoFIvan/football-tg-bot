"""Add section_id to products

Revision ID: 007
Revises: 006
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_label = None
depends_on = None


def upgrade():
    # Добавить section_id к products
    op.add_column('products', sa.Column(
        'section_id', sa.Integer(), nullable=True))
    op.create_foreign_key('products_section_id_fkey', 'products',
                          'sections', ['section_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Удалить связь с секциями
    op.drop_constraint('products_section_id_fkey',
                       'products', type_='foreignkey')
    op.drop_column('products', 'section_id')
