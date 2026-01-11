"""Remove product_id from reviews (reviews are now shop-wide)

Revision ID: 018
Revises: 017
Create Date: 2026-01-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_label = None
depends_on = None


def upgrade():
    # Drop foreign key constraint first
    op.drop_constraint('reviews_product_id_fkey', 'reviews', type_='foreignkey')

    # Drop product_id column from reviews table
    op.drop_column('reviews', 'product_id')


def downgrade():
    # Add product_id column back
    op.add_column('reviews', sa.Column('product_id', sa.Integer(), nullable=True))

    # Recreate foreign key constraint
    op.create_foreign_key('reviews_product_id_fkey', 'reviews', 'products',
                          ['product_id'], ['id'], ondelete='CASCADE')
