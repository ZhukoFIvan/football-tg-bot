"""
Статистика для администратора
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct
from pydantic import BaseModel
from typing import Optional

from core.db.session import get_db
from core.db.models import User, Order, Product, Section, Category
from core.dependencies import get_admin_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class OverviewStats(BaseModel):
    """Общая статистика"""
    total_users: int
    total_users_with_orders: int
    total_orders: int
    total_revenue: float
    total_products: int
    total_sections: int
    total_categories: int
    active_products: int
    out_of_stock_products: int


class UserStats(BaseModel):
    """Статистика пользователей"""
    total_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    banned_users: int
    admin_users: int


class OrderStats(BaseModel):
    """Статистика заказов"""
    total_orders: int
    pending_orders: int
    paid_orders: int
    completed_orders: int
    cancelled_orders: int
    orders_today: int
    orders_this_week: int
    orders_this_month: int


class RevenueStats(BaseModel):
    """Статистика выручки"""
    total_revenue: float
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    average_order_value: float
    currency: str = "RUB"


class ProductStats(BaseModel):
    """Статистика товаров"""
    total_products: int
    active_products: int
    inactive_products: int
    out_of_stock_products: int
    low_stock_products: int  # stock_count < 5
    total_stock_value: float


class TopProduct(BaseModel):
    """Топ товар"""
    product_id: int
    product_title: str
    orders_count: int
    revenue: float


# ==================== ENDPOINTS ====================

@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить общую статистику (dashboard overview)"""

    # Всего пользователей
    total_users = await db.scalar(select(func.count(User.id)))

    # Пользователи с заказами
    total_users_with_orders = await db.scalar(
        select(func.count(distinct(Order.user_id)))
    )

    # Всего заказов
    total_orders = await db.scalar(select(func.count(Order.id)))

    # Общая выручка (только paid и completed)
    total_revenue = await db.scalar(
        select(func.sum(Order.amount)).where(
            Order.status.in_(["paid", "completed"])
        )
    ) or 0.0

    # Товары
    total_products = await db.scalar(select(func.count(Product.id)))
    active_products = await db.scalar(
        select(func.count(Product.id)).where(Product.is_active == True)
    )
    out_of_stock_products = await db.scalar(
        select(func.count(Product.id)).where(Product.stock_count == 0)
    )

    # Разделы и категории
    total_sections = await db.scalar(select(func.count(Section.id)))
    total_categories = await db.scalar(select(func.count(Category.id)))

    return OverviewStats(
        total_users=total_users or 0,
        total_users_with_orders=total_users_with_orders or 0,
        total_orders=total_orders or 0,
        total_revenue=float(total_revenue),
        total_products=total_products or 0,
        total_sections=total_sections or 0,
        total_categories=total_categories or 0,
        active_products=active_products or 0,
        out_of_stock_products=out_of_stock_products or 0
    )


@router.get("/users", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить статистику пользователей"""

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Всего пользователей
    total_users = await db.scalar(select(func.count(User.id)))

    # Новые пользователи
    new_users_today = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_this_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    new_users_this_month = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )

    # Забаненные
    banned_users = await db.scalar(
        select(func.count(User.id)).where(User.is_banned == True)
    )

    # Админы
    admin_users = await db.scalar(
        select(func.count(User.id)).where(User.is_admin == True)
    )

    return UserStats(
        total_users=total_users or 0,
        new_users_today=new_users_today or 0,
        new_users_this_week=new_users_this_week or 0,
        new_users_this_month=new_users_this_month or 0,
        banned_users=banned_users or 0,
        admin_users=admin_users or 0
    )


@router.get("/orders", response_model=OrderStats)
async def get_order_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить статистику заказов"""

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Всего заказов
    total_orders = await db.scalar(select(func.count(Order.id)))

    # По статусам
    pending_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "pending")
    )
    paid_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "paid")
    )
    completed_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "completed")
    )
    cancelled_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "cancelled")
    )

    # По периодам
    orders_today = await db.scalar(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )
    orders_this_week = await db.scalar(
        select(func.count(Order.id)).where(Order.created_at >= week_start)
    )
    orders_this_month = await db.scalar(
        select(func.count(Order.id)).where(Order.created_at >= month_start)
    )

    return OrderStats(
        total_orders=total_orders or 0,
        pending_orders=pending_orders or 0,
        paid_orders=paid_orders or 0,
        completed_orders=completed_orders or 0,
        cancelled_orders=cancelled_orders or 0,
        orders_today=orders_today or 0,
        orders_this_week=orders_this_week or 0,
        orders_this_month=orders_this_month or 0
    )


@router.get("/revenue", response_model=RevenueStats)
async def get_revenue_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить статистику выручки"""

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Условие для оплаченных заказов
    paid_condition = Order.status.in_(["paid", "completed"])

    # Общая выручка
    total_revenue = await db.scalar(
        select(func.sum(Order.amount)).where(paid_condition)
    ) or 0.0

    # По периодам
    revenue_today = await db.scalar(
        select(func.sum(Order.amount)).where(
            and_(paid_condition, Order.created_at >= today_start)
        )
    ) or 0.0

    revenue_this_week = await db.scalar(
        select(func.sum(Order.amount)).where(
            and_(paid_condition, Order.created_at >= week_start)
        )
    ) or 0.0

    revenue_this_month = await db.scalar(
        select(func.sum(Order.amount)).where(
            and_(paid_condition, Order.created_at >= month_start)
        )
    ) or 0.0

    # Средний чек
    total_paid_orders = await db.scalar(
        select(func.count(Order.id)).where(paid_condition)
    ) or 0

    average_order_value = float(
        total_revenue) / total_paid_orders if total_paid_orders > 0 else 0.0

    return RevenueStats(
        total_revenue=float(total_revenue),
        revenue_today=float(revenue_today),
        revenue_this_week=float(revenue_this_week),
        revenue_this_month=float(revenue_this_month),
        average_order_value=average_order_value
    )


@router.get("/products", response_model=ProductStats)
async def get_product_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить статистику товаров"""

    # Всего товаров
    total_products = await db.scalar(select(func.count(Product.id)))

    # Активные/неактивные
    active_products = await db.scalar(
        select(func.count(Product.id)).where(Product.is_active == True)
    )
    inactive_products = await db.scalar(
        select(func.count(Product.id)).where(Product.is_active == False)
    )

    # Остатки
    out_of_stock_products = await db.scalar(
        select(func.count(Product.id)).where(Product.stock_count == 0)
    )
    low_stock_products = await db.scalar(
        select(func.count(Product.id)).where(
            and_(Product.stock_count > 0, Product.stock_count < 5)
        )
    )

    # Общая стоимость остатков
    result = await db.execute(
        select(func.sum(Product.price * Product.stock_count))
    )
    total_stock_value = result.scalar() or 0.0

    return ProductStats(
        total_products=total_products or 0,
        active_products=active_products or 0,
        inactive_products=inactive_products or 0,
        out_of_stock_products=out_of_stock_products or 0,
        low_stock_products=low_stock_products or 0,
        total_stock_value=float(total_stock_value)
    )


@router.get("/top-products")
async def get_top_products(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить топ товаров по продажам"""

    # Запрос с группировкой по товарам
    query = select(
        Product.id,
        Product.title,
        func.count(Order.id).label("orders_count"),
        func.sum(Order.amount).label("revenue")
    ).join(
        Order, Order.product_id == Product.id
    ).where(
        Order.status.in_(["paid", "completed"])
    ).group_by(
        Product.id, Product.title
    ).order_by(
        func.count(Order.id).desc()
    ).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        TopProduct(
            product_id=row.id,
            product_title=row.title,
            orders_count=row.orders_count,
            revenue=float(row.revenue or 0.0)
        )
        for row in rows
    ]


@router.get("/recent-users")
async def get_recent_users(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить последних зарегистрированных пользователей"""

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "is_banned": user.is_banned,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.get("/recent-orders")
async def get_recent_orders(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить последние заказы"""

    result = await db.execute(
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    orders = result.scalars().all()

    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "product_id": order.product_id,
            "status": order.status,
            "amount": float(order.amount),
            "currency": order.currency,
            "created_at": order.created_at
        }
        for order in orders
    ]
