"""Add source field to users table

Revision ID: 020
Revises: 019
Create Date: 2026-04-05

Tracks where the user registered from: 'telegram' (bot) or 'browser' (website)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_label = None
depends_on = None


def upgrade():
    # Add source column with default 'telegram' for all existing users
    op.add_column(
        'users',
        sa.Column(
            'source',
            sa.String(20),
            nullable=False,
            server_default='telegram'
        )
    )


def downgrade():
    op.drop_column('users', 'source')
