"""Add reviews system

Revision ID: 013
Revises: 012
Create Date: 2025-12-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_label = None
depends_on = None


def upgrade():
    # Создать таблицу reviews
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_product_id'),
                    'reviews', ['product_id'], unique=False)
    op.create_index(op.f('ix_reviews_user_id'),
                    'reviews', ['user_id'], unique=False)

    # Добавить поля рейтинга в products
    op.add_column('products', sa.Column('average_rating', sa.Numeric(
        precision=3, scale=2), nullable=False, server_default='0'))
    op.add_column('products', sa.Column('reviews_count',
                  sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    # Удалить поля рейтинга из products
    op.drop_column('products', 'reviews_count')
    op.drop_column('products', 'average_rating')

    # Удалить таблицу reviews
    op.drop_index(op.f('ix_reviews_user_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_product_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_id'), table_name='reviews')
    op.drop_table('reviews')

