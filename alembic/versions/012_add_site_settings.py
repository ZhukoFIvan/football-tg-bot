"""Add site settings table

Revision ID: 012
Revises: 011
Create Date: 2025-12-27
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_label = None
depends_on = None


def upgrade():
    # Создать таблицу site_settings
    op.create_table(
        'site_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_site_settings_id'),
                    'site_settings', ['id'], unique=False)
    op.create_index(op.f('ix_site_settings_key'),
                    'site_settings', ['key'], unique=True)

    # Добавить начальные настройки
    op.execute("""
        INSERT INTO site_settings (key, value, description, updated_at)
        VALUES ('snow_enabled', 'false', 'Включить снег на сайте', NOW())
    """)


def downgrade():
    op.drop_index(op.f('ix_site_settings_key'), table_name='site_settings')
    op.drop_index(op.f('ix_site_settings_id'), table_name='site_settings')
    op.drop_table('site_settings')

