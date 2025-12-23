"""Update product images and badge

Revision ID: 010
Revises: 009
Create Date: 2025-12-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_label = None
depends_on = None


def upgrade():
    # Удалить many-to-many связь с badges
    op.drop_table('product_badges')

    # Добавить badge_id как FK
    op.add_column('products', sa.Column(
        'badge_id', sa.Integer(), nullable=True))
    op.create_foreign_key('products_badge_id_fkey', 'products', 'badges', [
                          'badge_id'], ['id'], ondelete='SET NULL')

    # Переименовать image в images и изменить тип
    op.alter_column('products', 'image', new_column_name='images',
                    type_=sa.Text(), nullable=True)


def downgrade():
    # Удалить badge_id
    op.drop_constraint('products_badge_id_fkey',
                       'products', type_='foreignkey')
    op.drop_column('products', 'badge_id')

    # Вернуть image
    op.alter_column('products', 'images', new_column_name='image',
                    type_=sa.String(500), nullable=True)

    # Восстановить product_badges
    op.create_table(
        'product_badges',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['badge_id'], ['badges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'], ondelete='CASCADE')
    )
