"""
SQLAlchemy модели базы данных
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey,
    BigInteger, Text, Table
)
from sqlalchemy.orm import relationship
from core.db.base import Base


# Удалена many-to-many таблица product_badges
# Теперь у товара только один бейдж через badge_id


class User(Base):
    """Пользователи Telegram"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_banned = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    bonus_balance = Column(
        Integer, default=0, nullable=False)  # Бонусный баланс
    total_spent = Column(Numeric(10, 2), default=0,
                         nullable=False)  # Всего потрачено
    # Количество заказов
    total_orders = Column(Integer, default=0, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)
    bonus_transactions = relationship(
        "BonusTransaction", back_populates="user", cascade="all, delete-orphan")


class Section(Base):
    """Разделы каталога (верхний уровень) - максимум 3 секции"""
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Название секции
    image = Column(String(500), nullable=True)  # URL изображения секции
    # Роут для браузера (например: "sale", "new", "popular")
    route = Column(String(255), nullable=True)
    # Дата и время окончания акции (UTC)
    end_time = Column(DateTime, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Category(Base):
    """Категории - независимые от секций"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    main_image = Column(String(500), nullable=True)  # Основное изображение
    # Дополнительное изображение
    additional_image = Column(String(500), nullable=True)
    show_on_main = Column(Boolean, default=False,
                          nullable=False)  # Показывать на главной
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    """Товары (игровые ключи)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey(
        "categories.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey(
        # Связь с секцией (опционально)
        "sections.id", ondelete="SET NULL"), nullable=True)
    badge_id = Column(Integer, ForeignKey(
        "badges.id", ondelete="SET NULL"), nullable=True)  # Один бейдж
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # JSON массив URL изображений ["url1", "url2"]
    images = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    # Старая цена для отображения скидки
    old_price = Column(Numeric(10, 2), nullable=True)
    # Текст акции (например "Скидка 50%", "2 по цене 1")
    promotion_text = Column(String(200), nullable=True)
    currency = Column(String(10), default="RUB", nullable=False)
    stock_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Средний рейтинг (вычисляется из отзывов)
    average_rating = Column(Numeric(3, 2), default=0, nullable=False)
    # Количество отзывов
    reviews_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="products")
    section = relationship("Section")
    badge = relationship("Badge")
    reviews = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan")


class Badge(Base):
    """Бейджи для товаров (Новинка, Скидка 20%, Хит продаж и т.д.)"""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)  # "Скидка 20%", "Новинка"
    color = Column(String(50), default="#FF5722",
                   nullable=False)  # Цвет бейджа
    text_color = Column(String(50), default="#FFFFFF",
                        nullable=False)  # Цвет текста
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Banner(Base):
    """Баннеры для главной страницы"""
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=False)  # URL изображения баннера
    # Ссылка при клике (например на категорию)
    link = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Cart(Base):
    """Корзина пользователя"""
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart",
                         cascade="all, delete-orphan")


class CartItem(Base):
    """Товар в корзине"""
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey(
        "carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey(
        "products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")


class Order(Base):
    """Заказы пользователей"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    promo_code_id = Column(Integer, ForeignKey(
        "promo_codes.id", ondelete="SET NULL"), nullable=True)
    # pending, paid, completed, cancelled
    status = Column(String(50), default="pending", nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    promo_discount = Column(Numeric(10, 2), default=0, nullable=False)  # Скидка от промокода
    currency = Column(String(10), default="RUB", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="orders")
    promo_code = relationship("PromoCode", back_populates="orders")
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")


class OrderItem(Base):
    """Товар в заказе"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey(
        "orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey(
        "products.id", ondelete="SET NULL"), nullable=True)
    # Сохраняем название на момент покупки
    product_title = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)  # Цена на момент покупки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class BonusTransaction(Base):
    """История начисления и списания бонусов"""
    __tablename__ = "bonus_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey(
        "orders.id", ondelete="SET NULL"), nullable=True)
    # Положительное = начисление, отрицательное = списание
    amount = Column(Integer, nullable=False)
    # earned, spent, bonus_gift, refund
    type = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bonus_transactions")
    order = relationship("Order")


class SiteSettings(Base):
    """Глобальные настройки сайта (для всех пользователей)"""
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)


class Review(Base):
    """Отзывы на товары"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey(
        "products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # От 1 до 5 звёзд
    comment = Column(Text, nullable=True)  # Текст отзыва (опционально)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User")


class PromoCode(Base):
    """Промокоды для скидок"""
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # "SUMMER2025"
    discount_type = Column(String(20), nullable=False)  # "percent" или "fixed"
    discount_value = Column(Numeric(10, 2), nullable=False)  # 20 (для 20%) или 500 (для 500₽)
    min_order_amount = Column(Numeric(10, 2), nullable=True)  # Минимальная сумма заказа
    max_discount = Column(Numeric(10, 2), nullable=True)  # Максимальная скидка (для процентов)
    usage_limit = Column(Integer, nullable=True)  # Сколько раз можно использовать (null = безлимит)
    usage_count = Column(Integer, default=0, nullable=False)  # Сколько раз использовали
    valid_from = Column(DateTime, nullable=True)  # Дата начала действия
    valid_until = Column(DateTime, nullable=True)  # Дата окончания
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="promo_code")
