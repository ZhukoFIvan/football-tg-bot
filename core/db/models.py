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


# Many-to-Many таблица для связи товаров и бейджей
product_badges = Table(
    'product_badges',
    Base.metadata,
    Column('product_id', Integer, ForeignKey(
        'products.id', ondelete='CASCADE')),
    Column('badge_id', Integer, ForeignKey('badges.id', ondelete='CASCADE'))
)


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

    # Relationships
    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)


class Section(Base):
    """Разделы каталога (верхний уровень)"""
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    # URL фонового изображения
    background_image = Column(String(500), nullable=True)
    icon_image = Column(String(500), nullable=True)  # URL иконки/оформления
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    categories = relationship(
        "Category", back_populates="section", cascade="all, delete-orphan")


class Category(Base):
    """Категории внутри разделов"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey(
        "sections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)  # URL изображения категории
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    section = relationship("Section", back_populates="categories")
    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    """Товары (игровые ключи)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey(
        "categories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)  # URL изображения товара
    price = Column(Numeric(10, 2), nullable=False)
    # Старая цена для отображения скидки
    old_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), default="RUB", nullable=False)
    stock_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="products")
    badges = relationship("Badge", secondary=product_badges,
                          back_populates="products")


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

    # Relationships
    products = relationship(
        "Product", secondary=product_badges, back_populates="badges")


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
    # pending, paid, completed, cancelled
    status = Column(String(50), default="pending", nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="RUB", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="orders")
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
