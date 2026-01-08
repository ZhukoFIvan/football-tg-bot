"""Add is_priority field to products

Revision ID: 016
Revises: 015
Create Date: 2026-01-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_label = None
depends_on = None


def upgrade():
    # Add is_priority column to products table
    op.add_column('products', sa.Column('is_priority', sa.Boolean(),
                                        nullable=False, server_default='false'))


def downgrade():
    # Remove is_priority column from products table
    op.drop_column('products', 'is_priority')
