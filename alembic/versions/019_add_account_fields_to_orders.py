"""Add account fields to orders

Revision ID: 019
Revises: 018
Create Date: 2026-01-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_label = None
depends_on = None


def upgrade():
    # Add account information columns to orders table
    op.add_column('orders', sa.Column('account_type', sa.String(50), nullable=False, server_default='EA'))
    op.add_column('orders', sa.Column('account_email', sa.String(255), nullable=False, server_default=''))
    op.add_column('orders', sa.Column('account_password', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('account_name', sa.String(255), nullable=False, server_default=''))

    # Remove server_default after creating columns (they're only needed for existing records)
    op.alter_column('orders', 'account_type', server_default=None)
    op.alter_column('orders', 'account_email', server_default=None)
    op.alter_column('orders', 'account_name', server_default=None)


def downgrade():
    # Drop account information columns
    op.drop_column('orders', 'account_name')
    op.drop_column('orders', 'account_password')
    op.drop_column('orders', 'account_email')
    op.drop_column('orders', 'account_type')
