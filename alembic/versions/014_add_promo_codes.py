"""Add promo codes system

Revision ID: 014
Revises: 013
Create Date: 2025-01-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric, String, Integer, Boolean, DateTime


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_label = None
depends_on = None


def upgrade():
    # Создать таблицу promo_codes
    op.create_table(
        'promo_codes',
        sa.Column('id', Integer, primary_key=True, index=True),
        sa.Column('code', String(50), unique=True, nullable=False, index=True),
        sa.Column('discount_type', String(20), nullable=False),
        sa.Column('discount_value', Numeric(10, 2), nullable=False),
        sa.Column('min_order_amount', Numeric(10, 2), nullable=True),
        sa.Column('max_discount', Numeric(10, 2), nullable=True),
        sa.Column('usage_limit', Integer, nullable=True),
        sa.Column('usage_count', Integer, default=0, nullable=False),
        sa.Column('valid_from', DateTime, nullable=True),
        sa.Column('valid_until', DateTime, nullable=True),
        sa.Column('is_active', Boolean, default=True, nullable=False),
        sa.Column('created_at', DateTime, nullable=False),
        sa.Column('updated_at', DateTime, nullable=False)
    )

    # Добавить поля в orders
    op.add_column('orders', sa.Column('promo_code_id', Integer, nullable=True))
    op.add_column('orders', sa.Column('promo_discount', Numeric(10, 2), default=0, nullable=False))
    
    # Создать foreign key
    op.create_foreign_key(
        'fk_orders_promo_code_id',
        'orders', 'promo_codes',
        ['promo_code_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Удалить foreign key
    op.drop_constraint('fk_orders_promo_code_id', 'orders', type_='foreignkey')
    
    # Удалить поля из orders
    op.drop_column('orders', 'promo_discount')
    op.drop_column('orders', 'promo_code_id')
    
    # Удалить таблицу promo_codes
    op.drop_table('promo_codes')

