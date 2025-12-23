"""Update categories - remove section_id, add main_image and additional_image

Revision ID: 005
Revises: 004
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_label = None
depends_on = None


def upgrade():
    # Удалить связь с секциями
    op.drop_constraint('categories_section_id_fkey',
                       'categories', type_='foreignkey')
    op.drop_column('categories', 'section_id')

    # Переименовать image в main_image
    op.alter_column('categories', 'image', new_column_name='main_image')

    # Добавить additional_image
    op.add_column('categories', sa.Column(
        'additional_image', sa.String(length=500), nullable=True))


def downgrade():
    # Удалить additional_image
    op.drop_column('categories', 'additional_image')

    # Переименовать main_image обратно в image
    op.alter_column('categories', 'main_image', new_column_name='image')

    # Вернуть section_id
    op.add_column('categories', sa.Column(
        'section_id', sa.Integer(), nullable=True))
    op.create_foreign_key('categories_section_id_fkey', 'categories', 'sections', [
                          'section_id'], ['id'], ondelete='CASCADE')
