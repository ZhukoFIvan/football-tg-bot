"""
Эндпоинты для работы с промокодами
"""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field

from core.db.session import get_db
from core.db.models import PromoCode, User, Cart, CartItem, Product
from core.dependencies import get_current_user, get_admin_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class PromoCodeCreate(BaseModel):
    """Создание промокода (админ)"""
    code: str = Field(..., min_length=3, max_length=50, description="Код промокода (например SUMMER2025)")
    discount_type: str = Field(..., description="Тип скидки: percent или fixed")
    discount_value: float = Field(..., gt=0, description="Размер скидки (20 для 20% или 500 для 500₽)")
    min_order_amount: Optional[float] = Field(None, ge=0, description="Минимальная сумма заказа")
    max_discount: Optional[float] = Field(None, ge=0, description="Максимальная скидка (для процентов)")
    usage_limit: Optional[int] = Field(None, ge=1, description="Лимит использований (null = безлимит)")
    valid_from: Optional[datetime] = Field(None, description="Дата начала действия")
    valid_until: Optional[datetime] = Field(None, description="Дата окончания")
    is_active: bool = Field(True, description="Активен ли промокод")


class PromoCodeUpdate(BaseModel):
    """Обновление промокода (админ)"""
    code: Optional[str] = Field(None, min_length=3, max_length=50)
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    min_order_amount: Optional[float] = Field(None, ge=0)
    max_discount: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class PromoCodeResponse(BaseModel):
    """Ответ с промокодом"""
    id: int
    code: str
    discount_type: str
    discount_value: float
    min_order_amount: Optional[float]
    max_discount: Optional[float]
    usage_limit: Optional[int]
    usage_count: int
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplyPromoRequest(BaseModel):
    """Запрос на применение промокода"""
    code: str = Field(..., description="Код промокода")


class ApplyPromoResponse(BaseModel):
    """Ответ при применении промокода"""
    promo_code: str
    discount: float
    discount_type: str
    discount_value: float
    cart_total: float
    new_total: float


# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin/promo-codes", response_model=PromoCodeResponse)
async def create_promo_code(
    promo_data: PromoCodeCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать промокод (только для админов)
    
    **Параметры:**
    - code: Код промокода (например "SUMMER2025")
    - discount_type: "percent" (процент) или "fixed" (фиксированная сумма)
    - discount_value: Размер скидки (20 для 20% или 500 для 500₽)
    - min_order_amount: Минимальная сумма заказа (опционально)
    - max_discount: Максимальная скидка для процентов (опционально)
    - usage_limit: Лимит использований (опционально, null = безлимит)
    - valid_from: Дата начала действия (опционально)
    - valid_until: Дата окончания (опционально)
    - is_active: Активен ли промокод
    """
    # Проверить тип скидки
    if promo_data.discount_type not in ["percent", "fixed"]:
        raise HTTPException(
            status_code=400,
            detail="discount_type должен быть 'percent' или 'fixed'"
        )
    
    # Проверить размер процентной скидки
    if promo_data.discount_type == "percent" and promo_data.discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="Процентная скидка не может быть больше 100%"
        )
    
    # Проверить уникальность кода
    code_upper = promo_data.code.upper()
    existing = await db.execute(
        select(PromoCode).where(PromoCode.code == code_upper)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Промокод {code_upper} уже существует"
        )
    
    # Создать промокод
    promo = PromoCode(
        code=code_upper,
        discount_type=promo_data.discount_type,
        discount_value=Decimal(str(promo_data.discount_value)),
        min_order_amount=Decimal(str(promo_data.min_order_amount)) if promo_data.min_order_amount else None,
        max_discount=Decimal(str(promo_data.max_discount)) if promo_data.max_discount else None,
        usage_limit=promo_data.usage_limit,
        usage_count=0,
        valid_from=promo_data.valid_from,
        valid_until=promo_data.valid_until,
        is_active=promo_data.is_active
    )
    
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    
    return promo


@router.get("/admin/promo-codes", response_model=List[PromoCodeResponse])
async def get_promo_codes(
    limit: int = 100,
    offset: int = 0,
    is_active: Optional[bool] = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список промокодов (только для админов)
    
    **Параметры:**
    - limit: Количество записей (по умолчанию 100)
    - offset: Смещение (по умолчанию 0)
    - is_active: Фильтр по активности (опционально)
    """
    query = select(PromoCode)
    
    if is_active is not None:
        query = query.where(PromoCode.is_active == is_active)
    
    query = query.order_by(PromoCode.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    promo_codes = result.scalars().all()
    
    return promo_codes


@router.get("/admin/promo-codes/{promo_id}", response_model=PromoCodeResponse)
async def get_promo_code(
    promo_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить промокод по ID (только для админов)
    """
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_id)
    )
    promo = result.scalar_one_or_none()
    
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    return promo


@router.put("/admin/promo-codes/{promo_id}", response_model=PromoCodeResponse)
async def update_promo_code(
    promo_id: int,
    promo_data: PromoCodeUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить промокод (только для админов)
    """
    # Получить промокод
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_id)
    )
    promo = result.scalar_one_or_none()
    
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    # Обновить поля
    if promo_data.code is not None:
        code_upper = promo_data.code.upper()
        # Проверить уникальность нового кода
        existing = await db.execute(
            select(PromoCode).where(
                PromoCode.code == code_upper,
                PromoCode.id != promo_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Промокод {code_upper} уже существует"
            )
        promo.code = code_upper
    
    if promo_data.discount_type is not None:
        if promo_data.discount_type not in ["percent", "fixed"]:
            raise HTTPException(
                status_code=400,
                detail="discount_type должен быть 'percent' или 'fixed'"
            )
        promo.discount_type = promo_data.discount_type
    
    if promo_data.discount_value is not None:
        if promo.discount_type == "percent" and promo_data.discount_value > 100:
            raise HTTPException(
                status_code=400,
                detail="Процентная скидка не может быть больше 100%"
            )
        promo.discount_value = Decimal(str(promo_data.discount_value))
    
    if promo_data.min_order_amount is not None:
        promo.min_order_amount = Decimal(str(promo_data.min_order_amount))
    
    if promo_data.max_discount is not None:
        promo.max_discount = Decimal(str(promo_data.max_discount))
    
    if promo_data.usage_limit is not None:
        promo.usage_limit = promo_data.usage_limit
    
    if promo_data.valid_from is not None:
        promo.valid_from = promo_data.valid_from
    
    if promo_data.valid_until is not None:
        promo.valid_until = promo_data.valid_until
    
    if promo_data.is_active is not None:
        promo.is_active = promo_data.is_active
    
    await db.commit()
    await db.refresh(promo)
    
    return promo


@router.delete("/admin/promo-codes/{promo_id}")
async def delete_promo_code(
    promo_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить промокод (только для админов)
    """
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_id)
    )
    promo = result.scalar_one_or_none()
    
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    await db.delete(promo)
    await db.commit()
    
    return {"ok": True, "message": "Промокод удалён"}


# ==================== USER ENDPOINTS ====================

@router.post("/cart/apply-promo", response_model=ApplyPromoResponse)
async def apply_promo_code(
    request: ApplyPromoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Применить промокод к корзине
    
    **Параметры:**
    - code: Код промокода
    
    **Возвращает:**
    - promo_code: Код промокода
    - discount: Размер скидки в рублях
    - discount_type: Тип скидки (percent/fixed)
    - discount_value: Значение скидки (20 для 20% или 500 для 500₽)
    - cart_total: Сумма корзины до скидки
    - new_total: Сумма корзины после скидки
    """
    # Найти промокод
    code_upper = request.code.upper()
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == code_upper)
    )
    promo = result.scalar_one_or_none()
    
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    # Проверить активность
    if not promo.is_active:
        raise HTTPException(status_code=400, detail="Промокод неактивен")
    
    # Проверить срок действия
    now = datetime.utcnow()
    if promo.valid_from and now < promo.valid_from:
        raise HTTPException(
            status_code=400,
            detail=f"Промокод начнёт действовать с {promo.valid_from.strftime('%d.%m.%Y %H:%M')}"
        )
    
    if promo.valid_until and now > promo.valid_until:
        raise HTTPException(
            status_code=400,
            detail=f"Промокод истёк {promo.valid_until.strftime('%d.%m.%Y %H:%M')}"
        )
    
    # Проверить лимит использований
    if promo.usage_limit and promo.usage_count >= promo.usage_limit:
        raise HTTPException(
            status_code=400,
            detail="Промокод исчерпан"
        )
    
    # Получить корзину
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id)
    )
    cart = cart_result.scalar_one_or_none()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Корзина пуста")
    
    # Получить товары корзины
    items_result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    items = items_result.scalars().all()
    
    if not items:
        raise HTTPException(status_code=400, detail="Корзина пуста")
    
    # Загрузить товары
    product_ids = [item.product_id for item in items]
    products_result = await db.execute(
        select(Product).where(Product.id.in_(product_ids))
    )
    products_dict = {p.id: p for p in products_result.scalars().all()}
    
    # Рассчитать сумму корзины
    cart_total = Decimal('0')
    for item in items:
        product = products_dict.get(item.product_id)
        if product:
            cart_total += product.price * item.quantity
    
    # Проверить минимальную сумму заказа
    if promo.min_order_amount and cart_total < promo.min_order_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Минимальная сумма заказа для этого промокода: {float(promo.min_order_amount)} ₽"
        )
    
    # Рассчитать скидку
    if promo.discount_type == "percent":
        discount = cart_total * (promo.discount_value / Decimal('100'))
        # Применить максимальную скидку если есть
        if promo.max_discount:
            discount = min(discount, promo.max_discount)
    else:  # fixed
        discount = promo.discount_value
    
    # Скидка не может быть больше суммы корзины
    discount = min(discount, cart_total)
    
    new_total = cart_total - discount
    
    return ApplyPromoResponse(
        promo_code=promo.code,
        discount=float(discount),
        discount_type=promo.discount_type,
        discount_value=float(promo.discount_value),
        cart_total=float(cart_total),
        new_total=float(new_total)
    )


@router.post("/cart/validate-promo")
async def validate_promo_code(
    request: ApplyPromoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Проверить промокод без применения (для валидации на фронте)
    
    Возвращает те же данные что и apply-promo, но не сохраняет состояние
    """
    return await apply_promo_code(request, current_user, db)

