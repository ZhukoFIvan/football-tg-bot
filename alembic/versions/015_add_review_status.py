"""Add status field to reviews

Revision ID: 015
Revises: 014
Create Date: 2026-01-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_label = None
depends_on = None


def upgrade():
    # Add status column to reviews table
    op.add_column('reviews', sa.Column('status', sa.String(20),
                                       nullable=False, server_default='pending'))

    # Update existing reviews to 'approved' status (so they remain visible)
    op.execute("UPDATE reviews SET status = 'approved'")


def downgrade():
    # Remove status column from reviews table
    op.drop_column('reviews', 'status')
