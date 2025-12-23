"""
Публичные эндпоинты для каталога товаров
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.db.session import get_db
from core.db.models import Section, Category, Product

router = APIRouter()


# Pydantic схемы для ответов
class SectionResponse(BaseModel):
    id: int
    name: str
    image: Optional[str] = None
    route: Optional[str] = None
    # время до окончания акции в секундах (вычисляется)
    rest_time: Optional[int] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_rest_time(cls, section):
        """Создать response с вычисленным rest_time"""
        from datetime import datetime

        rest_time = None
        if section.end_time:
            # Вычислить оставшееся время в секундах
            now = datetime.utcnow()
            if section.end_time > now:
                rest_time = int((section.end_time - now).total_seconds())
            else:
                rest_time = 0

        return cls(
            id=section.id,
            name=section.name,
            image=section.image,
            route=section.route,
            rest_time=rest_time
        )


class CategoryResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    main_image: Optional[str] = None
    additional_image: Optional[str] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class BadgeResponse(BaseModel):
    id: int
    title: str
    color: str
    text_color: str

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    category_id: int
    section_id: Optional[int] = None
    title: str
    slug: str
    description: Optional[str] = None
    images: List[str] = []  # Массив URL изображений
    price: float
    old_price: Optional[float] = None  # Старая цена (для отображения скидки)
    promotion_text: Optional[str] = None  # Текст акции (например "Скидка 50%")
    currency: str
    stock_count: int
    is_active: bool
    badge: Optional[BadgeResponse] = None  # Один бейдж

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        import json
        # Парсим JSON массив изображений
        images = []
        if obj.images:
            try:
                images = json.loads(obj.images)
            except:
                images = []

        return cls(
            id=obj.id,
            category_id=obj.category_id,
            section_id=obj.section_id,
            title=obj.title,
            slug=obj.slug,
            description=obj.description,
            images=images,
            price=float(obj.price),
            old_price=float(obj.old_price) if obj.old_price else None,
            promotion_text=obj.promotion_text,
            currency=obj.currency,
            stock_count=obj.stock_count,
            is_active=obj.is_active,
            badge=BadgeResponse.from_orm(obj.badge) if obj.badge else None
        )


@router.get("/sections", response_model=List[SectionResponse])
async def get_sections(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех активных разделов
    rest_time вычисляется автоматически на основе end_time
    """
    result = await db.execute(
        select(Section)
        .where(Section.is_active == True)
        .order_by(Section.sort_order, Section.id)
    )
    sections = result.scalars().all()

    # Вычислить rest_time для каждой секции
    return [SectionResponse.from_orm_with_rest_time(section) for section in sections]


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех активных категорий
    """
    query = select(Category).where(Category.is_active == True)
    query = query.order_by(Category.sort_order, Category.id)

    result = await db.execute(query)
    categories = result.scalars().all()
    return categories


@router.get("/products", response_model=List[ProductResponse])
async def get_products(
    category_id: Optional[int] = None,
    section_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список товаров

    Фильтры:
    - category_id: фильтр по категории
    - section_id: фильтр по секции
    """
    from sqlalchemy.orm import selectinload

    query = select(Product).where(Product.is_active == True)

    # Подгрузить badge для каждого товара
    query = query.options(selectinload(Product.badge))

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if section_id is not None:
        query = query.where(Product.section_id == section_id)

    query = query.order_by(Product.id.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductResponse.from_orm(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о товаре
    """
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product
