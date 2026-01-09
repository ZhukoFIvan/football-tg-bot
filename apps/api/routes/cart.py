"""
Корзина пользователя
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from decimal import Decimal

from core.db.session import get_db
from core.db.models import Cart, CartItem, Product, User, Order, OrderItem, PromoCode, BonusTransaction, Payment
from core.dependencies import get_current_user
from core.bonus import BonusSystem
from core.config import settings
from core.payments.freekassa import FreeKassaProvider
from core.payments.paypalych import PaypalychProvider
from datetime import datetime

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class CartItemResponse(BaseModel):
    """Товар в корзине"""
    id: int
    product_id: int
    product_title: str
    product_image: str | None
    product_price: Decimal
    product_old_price: Decimal | None
    quantity: int
    subtotal: Decimal  # price * quantity

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Корзина пользователя"""
    id: int
    items: List[CartItemResponse]
    total_items: int  # Общее количество товаров
    total_amount: Decimal  # Общая сумма
    bonus_balance: int  # Доступные бонусы пользователя
    max_bonus_usage: int  # Максимум бонусов можно использовать
    bonus_will_earn: int  # Сколько бонусов будет начислено за эту покупку


class AddToCartRequest(BaseModel):
    """Добавить товар в корзину"""
    product_id: int
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    """Обновить количество товара"""
    quantity: int


class CreatePaymentRequest(BaseModel):
    """Создать платеж для корзины"""
    provider: str  # "freekassa" или "paypalych"
    payment_method: str  # "card" для карты, "sbp" для СБП
    promo_code: str | None = None
    bonus_to_use: int = 0


class PaymentResponse(BaseModel):
    """Ответ с данными платежа"""
    payment_id: str
    payment_url: str
    order_id: int
    amount: Decimal
    status: str


# ==================== HELPER FUNCTIONS ====================

async def get_or_create_cart(user: User, db: AsyncSession) -> Cart:
    """Получить или создать корзину для пользователя"""
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one_or_none()

    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    return cart


async def format_cart_response(cart: Cart, user: User) -> CartResponse:
    """Форматировать ответ с корзиной"""
    items = []
    total_items = 0
    total_amount = Decimal(0)

    for cart_item in cart.items:
        product = cart_item.product
        if not product or not product.is_active:
            continue

        subtotal = product.price * cart_item.quantity
        total_items += cart_item.quantity
        total_amount += subtotal

        # Получить первое изображение из массива
        import json
        product_image = None
        if product.images:
            try:
                images_list = json.loads(product.images)
                product_image = images_list[0] if images_list else None
            except:
                product_image = None

        items.append(CartItemResponse(
            id=cart_item.id,
            product_id=product.id,
            product_title=product.title,
            product_image=product_image,
            product_price=product.price,
            product_old_price=product.old_price,
            quantity=cart_item.quantity,
            subtotal=subtotal
        ))

    # Рассчитать бонусы
    max_bonus_usage = await BonusSystem.calculate_max_bonus_usage(total_amount)
    
    # Рассчитать начисление бонусов (зависит только от количества покупок)
    bonus_will_earn = await BonusSystem.calculate_earned_bonuses(total_amount, user)

    return CartResponse(
        id=cart.id,
        items=items,
        total_items=total_items,
        total_amount=total_amount,
        bonus_balance=user.bonus_balance,
        max_bonus_usage=max_bonus_usage,
        bonus_will_earn=bonus_will_earn
    )


# ==================== ENDPOINTS ====================

@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить корзину текущего пользователя
    """
    cart = await get_or_create_cart(current_user, db)
    return await format_cart_response(cart, current_user)


@router.post("/items", response_model=CartResponse)
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Добавить товар в корзину
    Если товар уже есть - увеличить количество
    """
    if request.quantity < 1:
        raise HTTPException(
            status_code=400, detail="Quantity must be at least 1")

    # Проверить существование товара
    result = await db.execute(
        select(Product).where(Product.id == request.product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.is_active:
        raise HTTPException(status_code=400, detail="Product is not available")

    # Получить корзину
    cart = await get_or_create_cart(current_user, db)

    # Проверить есть ли товар уже в корзине
    result = await db.execute(
        select(CartItem)
        .where(CartItem.cart_id == cart.id, CartItem.product_id == request.product_id)
    )
    cart_item = result.scalar_one_or_none()

    if cart_item:
        # Увеличить количество
        cart_item.quantity += request.quantity
    else:
        # Добавить новый товар
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=request.product_id,
            quantity=request.quantity
        )
        db.add(cart_item)

    await db.commit()

    # Перезагрузить корзину с товарами
    await db.refresh(cart)
    result = await db.execute(
        select(Cart)
        .where(Cart.id == cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one()

    return await format_cart_response(cart, current_user)


@router.patch("/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: int,
    request: UpdateCartItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить количество товара в корзине
    """
    if request.quantity < 1:
        raise HTTPException(
            status_code=400, detail="Quantity must be at least 1")

    # Получить корзину
    cart = await get_or_create_cart(current_user, db)

    # Найти товар в корзине
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Обновить количество
    cart_item.quantity = request.quantity
    await db.commit()

    # Перезагрузить корзину
    result = await db.execute(
        select(Cart)
        .where(Cart.id == cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one()

    return await format_cart_response(cart, current_user)


@router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить товар из корзины
    """
    # Получить корзину
    cart = await get_or_create_cart(current_user, db)

    # Найти товар в корзине
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Удалить товар
    await db.delete(cart_item)
    await db.commit()

    # Перезагрузить корзину
    result = await db.execute(
        select(Cart)
        .where(Cart.id == cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one()

    return await format_cart_response(cart, current_user)


@router.delete("/", response_model=dict)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Очистить всю корзину
    """
    # Получить корзину
    cart = await get_or_create_cart(current_user, db)

    # Удалить все товары
    for item in cart.items:
        await db.delete(item)

    await db.commit()

    return {"ok": True, "message": "Cart cleared"}


@router.post("/checkout", response_model=PaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать платеж для корзины
    
    Сначала создает заказ из корзины, затем создает платеж через выбранный провайдер.
    Поддерживает оплату через FreeKassa и PayPalych по карте и СБП.
    """
    # Валидация провайдера и метода оплаты
    if request.provider not in ["freekassa", "paypalych"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Supported: freekassa, paypalych"
        )
    
    if request.payment_method not in ["card", "sbp"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method. Supported: card, sbp"
        )

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

    # Применить промокод и бонусы
    promo_discount = Decimal(0)
    promo_code_id = None
    
    if request.promo_code:
        code_upper = request.promo_code.upper()
        promo_result = await db.execute(
            select(PromoCode).where(PromoCode.code == code_upper)
        )
        promo = promo_result.scalar_one_or_none()
        
        if promo and promo.is_active:
            now = datetime.utcnow()
            if (not promo.valid_from or now >= promo.valid_from) and \
               (not promo.valid_until or now <= promo.valid_until):
                if not promo.usage_limit or promo.usage_count < promo.usage_limit:
                    if not promo.min_order_amount or total_amount >= promo.min_order_amount:
                        if promo.discount_type == "percent":
                            promo_discount = total_amount * (promo.discount_value / Decimal('100'))
                            if promo.max_discount:
                                promo_discount = min(promo_discount, promo.max_discount)
                        else:
                            promo_discount = promo.discount_value
                        promo_discount = min(promo_discount, total_amount)
                        promo_code_id = promo.id
                        promo.usage_count += 1

    total_after_promo = total_amount - promo_discount

    # Рассчитать применение бонусов (но НЕ списывать их сейчас!)
    bonus_used = 0
    bonus_discount = Decimal(0)
    
    if request.bonus_to_use > 0:
        if request.bonus_to_use > current_user.bonus_balance:
            bonus_used = current_user.bonus_balance
        else:
            bonus_used = request.bonus_to_use
        
        max_bonus = await BonusSystem.calculate_max_bonus_usage(total_after_promo)
        if bonus_used > max_bonus:
            bonus_used = max_bonus
        
        bonus_discount = Decimal(bonus_used * BonusSystem.BONUS_TO_RUBLE)
        # НЕ списываем бонусы здесь! Они спишутся после успешной оплаты в webhook

    final_amount = total_after_promo - bonus_discount
    final_amount = max(Decimal(0), final_amount)

    # Рассчитать начисление бонусов
    earned_bonuses = await BonusSystem.calculate_earned_bonuses(final_amount, current_user)

    # Создать заказ
    order = Order(
        user_id=current_user.id,
        promo_code_id=promo_code_id,
        promo_discount=promo_discount,
        status="pending",
        total_amount=total_amount,  # Исходная сумма
        bonus_used=bonus_used,  # Использовано бонусов
        bonus_earned=earned_bonuses,  # Начислено бонусов
        final_amount=final_amount,  # Итоговая сумма к оплате
        currency="RUB"
    )
    db.add(order)
    await db.flush()

    # Создать товары заказа
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            **item_data
        )
        db.add(order_item)

    # Уменьшить остатки товаров
    for cart_item in cart.items:
        product = cart_item.product
        product.stock_count -= cart_item.quantity

    # НЕ создаем бонусные транзакции и НЕ обновляем статистику здесь!
    # Это будет сделано в webhook после успешной оплаты

    # Очистить корзину
    for cart_item in cart.items:
        await db.delete(cart_item)

    await db.commit()
    await db.refresh(order)

    # Создать платеж через выбранный провайдер
    # Формируем описание с названиями товаров
    product_titles = [item["product_title"] for item in order_items_data]
    if len(product_titles) == 1:
        description = f"Заказ #{order.id} - {product_titles[0]}"
    elif len(product_titles) <= 3:
        description = f"Заказ #{order.id} - {', '.join(product_titles)}"
    else:
        description = f"Заказ #{order.id} - {', '.join(product_titles[:2])} и еще {len(product_titles) - 2} товар(ов)"
    
    if request.provider == "freekassa":
        if not settings.FREEKASSA_MERCHANT_ID or not settings.FREEKASSA_SECRET_KEY or not settings.FREEKASSA_SECRET_KEY2:
            raise HTTPException(
                status_code=500,
                detail="FreeKassa is not configured. Please set FREEKASSA_MERCHANT_ID, FREEKASSA_SECRET_KEY and FREEKASSA_SECRET_KEY2"
            )
        provider = FreeKassaProvider(
            merchant_id=settings.FREEKASSA_MERCHANT_ID,
            secret_key=settings.FREEKASSA_SECRET_KEY,
            secret_key2=settings.FREEKASSA_SECRET_KEY2
        )
    elif request.provider == "paypalych":
        if not settings.PAYPALYCH_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="PayPaly is not configured. Please set PAYPALYCH_API_KEY"
            )
        provider = PaypalychProvider(
            api_key=settings.PAYPALYCH_API_KEY
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")

    # Создать платеж
    payment_data = await provider.create_payment(
        order_id=order.id,
        amount=final_amount,
        currency="RUB",
        description=description,
        user_id=current_user.id,
        payment_method=request.payment_method
    )

    # Сохранить платеж в БД
    payment = Payment(
        order_id=order.id,
        user_id=current_user.id,
        payment_id=payment_data["payment_id"],
        provider=request.provider,
        payment_method=request.payment_method,
        amount=final_amount,
        currency="RUB",
        status=payment_data["status"],
        payment_url=payment_data["payment_url"],
        description=description
    )
    db.add(payment)
    await db.commit()

    return PaymentResponse(
        payment_id=payment_data["payment_id"],
        payment_url=payment_data["payment_url"],
        order_id=order.id,
        amount=final_amount,
        status=payment_data["status"]
    )
