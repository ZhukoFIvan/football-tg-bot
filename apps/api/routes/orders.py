"""
Заказы пользователя
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

from core.db.session import get_db
from core.db.models import Cart, CartItem, Order, OrderItem, Product, User, PromoCode, BonusTransaction
from core.dependencies import get_current_user
from core.bonus import BonusSystem

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
    promo_code: str | None = None  # Промокод (опционально)
    bonus_to_use: int = 0  # Количество бонусов к использованию


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

    # ==================== ПРИМЕНИТЬ ПРОМОКОД ====================
    promo_discount = Decimal(0)
    promo_code_id = None
    
    if request.promo_code:
        code_upper = request.promo_code.upper()
        promo_result = await db.execute(
            select(PromoCode).where(PromoCode.code == code_upper)
        )
        promo = promo_result.scalar_one_or_none()
        
        if promo and promo.is_active:
            # Проверить срок действия
            now = datetime.utcnow()
            if (not promo.valid_from or now >= promo.valid_from) and \
               (not promo.valid_until or now <= promo.valid_until):
                
                # Проверить лимит использований
                if not promo.usage_limit or promo.usage_count < promo.usage_limit:
                    
                    # Проверить минимальную сумму
                    if not promo.min_order_amount or total_amount >= promo.min_order_amount:
                        
                        # Рассчитать скидку
                        if promo.discount_type == "percent":
                            promo_discount = total_amount * (promo.discount_value / Decimal('100'))
                            if promo.max_discount:
                                promo_discount = min(promo_discount, promo.max_discount)
                        else:  # fixed
                            promo_discount = promo.discount_value
                        
                        # Скидка не может быть больше суммы
                        promo_discount = min(promo_discount, total_amount)
                        promo_code_id = promo.id
                        
                        # Увеличить счётчик использований
                        promo.usage_count += 1

    # Применить скидку от промокода
    total_after_promo = total_amount - promo_discount

    # ==================== ПРИМЕНИТЬ БОНУСЫ ====================
    bonus_used = 0
    bonus_discount = Decimal(0)
    
    if request.bonus_to_use > 0:
        # Проверить доступность бонусов
        if request.bonus_to_use > current_user.bonus_balance:
            bonus_used = current_user.bonus_balance
        else:
            bonus_used = request.bonus_to_use
        
        # Проверить максимальное использование (50% от суммы после промокода)
        max_bonus = await BonusSystem.calculate_max_bonus_usage(total_after_promo)
        if bonus_used > max_bonus:
            bonus_used = max_bonus
        
        bonus_discount = Decimal(bonus_used * BonusSystem.BONUS_TO_RUBLE)
        
        # Списать бонусы
        current_user.bonus_balance -= bonus_used

    # Итоговая сумма = сумма товаров - промокод - бонусы
    final_amount = total_after_promo - bonus_discount
    final_amount = max(Decimal(0), final_amount)  # Не может быть отрицательной

    # Создать заказ
    order = Order(
        user_id=current_user.id,
        promo_code_id=promo_code_id,
        promo_discount=promo_discount,
        status="pending",
        total_amount=final_amount,
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

    # ==================== БОНУСНЫЕ ТРАНЗАКЦИИ ====================
    
    # Создать транзакцию списания бонусов (если использовались)
    if bonus_used > 0:
        bonus_spent_tx = BonusTransaction(
            user_id=current_user.id,
            order_id=order.id,
            amount=-bonus_used,
            type="spent",
            description=f"Списание бонусов за заказ #{order.id}"
        )
        db.add(bonus_spent_tx)
    
    # Рассчитать начисление бонусов (от итоговой суммы)
    earned_bonuses = await BonusSystem.calculate_earned_bonuses(final_amount, current_user)
    
    if earned_bonuses > 0:
        # Начислить бонусы
        current_user.bonus_balance += earned_bonuses
        
        # Создать транзакцию начисления
        bonus_earned_tx = BonusTransaction(
            user_id=current_user.id,
            order_id=order.id,
            amount=earned_bonuses,
            type="earned",
            description=f"Начисление бонусов за заказ #{order.id}"
        )
        db.add(bonus_earned_tx)
    
    # Обновить статистику пользователя
    current_user.total_spent += final_amount
    current_user.total_orders += 1

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
    
    # Обновить статус платежа, если есть
    from core.db.models import Payment
    payment_result = await db.execute(
        select(Payment).where(Payment.order_id == order_id)
    )
    payment = payment_result.scalar_one_or_none()
    if payment and payment.status == "pending":
        payment.status = "cancelled"
        payment.cancelled_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(order)
    
    # Отправить уведомление пользователю в Telegram
    try:
        from aiogram import Bot
        from aiogram.enums import ParseMode
        from core.config import settings
        bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
        message = f"""
❌ <b>Заказ отменен</b>

📦 Заказ #{order_id}
💰 Сумма: {float(order.total_amount):,.2f} ₽

Заказ был отменен. Товары возвращены на склад.
"""
        await bot.send_message(chat_id=current_user.telegram_id, text=message)
        await bot.session.close()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при отправке уведомления об отмене заказа: {e}")

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
