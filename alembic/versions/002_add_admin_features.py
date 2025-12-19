"""Add admin features (badges, banners, images, orders)

Revision ID: 002
Revises: 001
Create Date: 2025-12-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавить поля к users
    op.add_column('users', sa.Column('is_admin', sa.Boolean(),
                  nullable=False, server_default='false'))

    # Добавить поля к sections
    op.add_column('sections', sa.Column(
        'description', sa.Text(), nullable=True))
    op.add_column('sections', sa.Column(
        'background_image', sa.String(length=500), nullable=True))
    op.add_column('sections', sa.Column(
        'icon_image', sa.String(length=500), nullable=True))

    # Добавить поля к categories
    op.add_column('categories', sa.Column(
        'description', sa.Text(), nullable=True))
    op.add_column('categories', sa.Column(
        'image', sa.String(length=500), nullable=True))

    # Добавить поля к products
    op.add_column('products', sa.Column(
        'image', sa.String(length=500), nullable=True))
    op.add_column('products', sa.Column(
        'old_price', sa.Numeric(precision=10, scale=2), nullable=True))

    # Создание таблицы badges
    op.create_table(
        'badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=50),
                  nullable=False, server_default='#FF5722'),
        sa.Column('text_color', sa.String(length=50),
                  nullable=False, server_default='#FFFFFF'),
        sa.Column('is_active', sa.Boolean(),
                  nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_badges_id'), 'badges', ['id'], unique=False)

    # Создание таблицы product_badges (many-to-many)
    op.create_table(
        'product_badges',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['badge_id'], ['badges.id'], ondelete='CASCADE')
    )

    # Создание таблицы banners
    op.create_table(
        'banners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image', sa.String(length=500), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(),
                  nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(),
                  nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_banners_id'), 'banners', ['id'], unique=False)

    # Создание таблицы orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50),
                  nullable=False, server_default='pending'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10),
                  nullable=False, server_default='RUB'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)


def downgrade() -> None:
    # Удалить таблицы
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')

    op.drop_index(op.f('ix_banners_id'), table_name='banners')
    op.drop_table('banners')

    op.drop_table('product_badges')

    op.drop_index(op.f('ix_badges_id'), table_name='badges')
    op.drop_table('badges')

    # Удалить колонки из products
    op.drop_column('products', 'old_price')
    op.drop_column('products', 'image')

    # Удалить колонки из categories
    op.drop_column('categories', 'image')
    op.drop_column('categories', 'description')

    # Удалить колонки из sections
    op.drop_column('sections', 'icon_image')
    op.drop_column('sections', 'background_image')
    op.drop_column('sections', 'description')

    # Удалить колонки из users
    op.drop_column('users', 'is_admin')
