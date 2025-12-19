"""
Заказы пользователя
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from core.db.session import get_db
from core.db.models import Cart, CartItem, Order, OrderItem, Product, User
from core.dependencies import get_current_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class OrderItemResponse(BaseModel):
    """Товар в заказе"""
    id: int
    product_id: int | None
    product_title: str
    quantity: int
    price: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Заказ"""
    id: int
    status: str
    total_amount: Decimal
    currency: str
    items: List[OrderItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateOrderRequest(BaseModel):
    """Создать заказ из корзины"""
    pass  # Пока без дополнительных параметров


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[OrderResponse])
async def get_my_orders(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список заказов текущего пользователя
    """
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()

    return [
        OrderResponse(
            id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            currency=order.currency,
            items=[
                OrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_title=item.product_title,
                    quantity=item.quantity,
                    price=item.price
                )
                for item in order.items
            ],
            created_at=order.created_at
        )
        for order in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детали заказа
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=item.product_title,
                quantity=item.quantity,
                price=item.price
            )
            for item in order.items
        ],
        created_at=order.created_at
    )


@router.post("/", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать заказ из корзины

    1. Проверяет что корзина не пустая
    2. Проверяет наличие товаров на складе
    3. Создает заказ со статусом "pending"
    4. Очищает корзину
    """
    # Получить корзину с товарами
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Проверить товары и подсчитать сумму
    order_items_data = []
    total_amount = Decimal(0)

    for cart_item in cart.items:
        product = cart_item.product

        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {cart_item.product_id} not found"
            )

        if not product.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.title}' is not available"
            )

        if product.stock_count < cart_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for '{product.title}'. Available: {product.stock_count}"
            )

        subtotal = product.price * cart_item.quantity
        total_amount += subtotal

        order_items_data.append({
            "product_id": product.id,
            "product_title": product.title,
            "quantity": cart_item.quantity,
            "price": product.price
        })

    # Создать заказ
    order = Order(
        user_id=current_user.id,
        status="pending",
        total_amount=total_amount,
        currency="RUB"
    )
    db.add(order)
    await db.flush()  # Получить order.id

    # Создать товары заказа
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            **item_data
        )
        db.add(order_item)

    # Уменьшить остатки товаров (резервируем)
    for cart_item in cart.items:
        product = cart_item.product
        product.stock_count -= cart_item.quantity

    # Очистить корзину
    for cart_item in cart.items:
        await db.delete(cart_item)

    await db.commit()
    await db.refresh(order)

    # Загрузить товары заказа
    result = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one()

    return OrderResponse(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=item.product_title,
                quantity=item.quantity,
                price=item.price
            )
            for item in order.items
        ],
        created_at=order.created_at
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отменить заказ (только если статус pending)
    Возвращает товары на склад
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status '{order.status}'"
        )

    # Вернуть товары на склад
    for item in order.items:
        if item.product:
            item.product.stock_count += item.quantity

    # Обновить статус
    order.status = "cancelled"
    await db.commit()
    await db.refresh(order)

    return OrderResponse(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_title=item.product_title,
                quantity=item.quantity,
                price=item.price
            )
            for item in order.items
        ],
        created_at=order.created_at
    )
