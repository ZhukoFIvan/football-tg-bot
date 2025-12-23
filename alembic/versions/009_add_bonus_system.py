"""Add bonus system

Revision ID: 009
Revises: 008
Create Date: 2025-12-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_label = None
depends_on = None


def upgrade():
    # Добавить поля бонусов в users
    op.add_column('users', sa.Column('bonus_balance', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_spent', sa.Numeric(10, 2), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_orders', sa.Integer(), nullable=False, server_default='0'))
    
    # Удалить server_default после создания
    op.alter_column('users', 'bonus_balance', server_default=None)
    op.alter_column('users', 'total_spent', server_default=None)
    op.alter_column('users', 'total_orders', server_default=None)
    
    # Добавить поля бонусов в orders
    op.add_column('orders', sa.Column('bonus_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('bonus_earned', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('final_amount', sa.Numeric(10, 2), nullable=False, server_default='0'))
    
    # Удалить server_default после создания
    op.alter_column('orders', 'bonus_used', server_default=None)
    op.alter_column('orders', 'bonus_earned', server_default=None)
    op.alter_column('orders', 'final_amount', server_default=None)
    
    # Создать таблицу bonus_transactions
    op.create_table(
        'bonus_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bonus_transactions_id'), 'bonus_transactions', ['id'], unique=False)


def downgrade():
    # Удалить таблицу bonus_transactions
    op.drop_index(op.f('ix_bonus_transactions_id'), table_name='bonus_transactions')
    op.drop_table('bonus_transactions')
    
    # Удалить поля из orders
    op.drop_column('orders', 'final_amount')
    op.drop_column('orders', 'bonus_earned')
    op.drop_column('orders', 'bonus_used')
    
    # Удалить поля из users
    op.drop_column('users', 'total_orders')
    op.drop_column('users', 'total_spent')
    op.drop_column('users', 'bonus_balance')
