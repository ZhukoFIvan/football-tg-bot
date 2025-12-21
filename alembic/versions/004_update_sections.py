"""Update sections structure

Revision ID: 004_update_sections
Revises: 003_add_cart_and_orders
Create Date: 2025-12-20
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_update_sections'
down_revision = '003_add_cart_and_orders'
branch_label = None
depends_on = None


def upgrade():
    # Удалить старые колонки
    op.drop_column('sections', 'title')
    op.drop_column('sections', 'slug')
    op.drop_column('sections', 'description')
    op.drop_column('sections', 'background_image')
    op.drop_column('sections', 'icon_image')

    # Добавить новые колонки
    op.add_column('sections', sa.Column('name', sa.String(
        length=255), nullable=False, server_default='Section'))
    op.add_column('sections', sa.Column(
        'image', sa.String(length=500), nullable=True))
    op.add_column('sections', sa.Column(
        'route', sa.String(length=255), nullable=True))
    op.add_column('sections', sa.Column(
        'rest_time', sa.Integer(), nullable=True))

    # Удалить server_default после создания
    op.alter_column('sections', 'name', server_default=None)


def downgrade():
    # Удалить новые колонки
    op.drop_column('sections', 'rest_time')
    op.drop_column('sections', 'route')
    op.drop_column('sections', 'image')
    op.drop_column('sections', 'name')

    # Вернуть старые колонки
    op.add_column('sections', sa.Column(
        'icon_image', sa.String(length=500), nullable=True))
    op.add_column('sections', sa.Column('background_image',
                  sa.String(length=500), nullable=True))
    op.add_column('sections', sa.Column(
        'description', sa.Text(), nullable=True))
    op.add_column('sections', sa.Column('slug', sa.String(
        length=255), nullable=False, server_default='section'))
    op.add_column('sections', sa.Column('title', sa.String(
        length=255), nullable=False, server_default='Section'))

    # Удалить server_default
    op.alter_column('sections', 'slug', server_default=None)
    op.alter_column('sections', 'title', server_default=None)
