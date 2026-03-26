"""Add web auth fields to users (email, password, display_name, make telegram_id nullable)

Revision ID: 020
Revises: 019
Create Date: 2026-03-26
"""
from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make telegram_id nullable (web users won't have it)
    op.alter_column('users', 'telegram_id', nullable=True)

    # Add web auth fields
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))

    # Unique index on email (Postgres allows multiple NULLs in unique index)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
    op.alter_column('users', 'telegram_id', nullable=False)
