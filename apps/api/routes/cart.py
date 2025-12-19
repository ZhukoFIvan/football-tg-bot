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
from core.db.models import Cart, CartItem, Product, User
from core.dependencies import get_current_user

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


class AddToCartRequest(BaseModel):
    """Добавить товар в корзину"""
    product_id: int
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    """Обновить количество товара"""
    quantity: int


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


def format_cart_response(cart: Cart) -> CartResponse:
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

        items.append(CartItemResponse(
            id=cart_item.id,
            product_id=product.id,
            product_title=product.title,
            product_image=product.image,
            product_price=product.price,
            product_old_price=product.old_price,
            quantity=cart_item.quantity,
            subtotal=subtotal
        ))

    return CartResponse(
        id=cart.id,
        items=items,
        total_items=total_items,
        total_amount=total_amount
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
    return format_cart_response(cart)


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

    return format_cart_response(cart)


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

    return format_cart_response(cart)


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

    return format_cart_response(cart)


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
