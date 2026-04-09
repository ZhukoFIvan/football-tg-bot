"""Add media support to chat messages

Revision ID: 022
Revises: 021
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('message_type', sa.String(10), nullable=False, server_default='text'))
    op.add_column('chat_messages', sa.Column('media_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_messages', 'media_url')
    op.drop_column('chat_messages', 'message_type')
