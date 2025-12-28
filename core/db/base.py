"""
SQLAlchemy Base и импорты моделей
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Импортируем все модели здесь для Alembic
# Импорт должен быть после создания Base, но models.py уже импортирует Base
# Поэтому импортируем модели только когда они нужны (в alembic/env.py)


def import_models():
    """Импорт всех моделей для Alembic"""
    from core.db.models import (  # noqa
        User, Section, Category, Product, Badge, Banner,
        Cart, CartItem, Order, OrderItem, BonusTransaction, SiteSettings
    )
