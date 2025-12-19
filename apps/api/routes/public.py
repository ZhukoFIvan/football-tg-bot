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
    title: str
    slug: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    id: int
    section_id: int
    title: str
    slug: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    category_id: int
    title: str
    slug: str
    description: Optional[str]
    price: float
    currency: str
    stock_count: int
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/sections", response_model=List[SectionResponse])
async def get_sections(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех активных разделов
    """
    result = await db.execute(
        select(Section)
        .where(Section.is_active == True)
        .order_by(Section.sort_order, Section.id)
    )
    sections = result.scalars().all()
    return sections


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    section_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список категорий
    Если указан section_id - фильтрует по разделу
    """
    query = select(Category).where(Category.is_active == True)

    if section_id is not None:
        query = query.where(Category.section_id == section_id)

    query = query.order_by(Category.sort_order, Category.id)

    result = await db.execute(query)
    categories = result.scalars().all()
    return categories


@router.get("/products", response_model=List[ProductResponse])
async def get_products(
    category_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список товаров
    Если указан category_id - фильтрует по категории
    """
    query = select(Product).where(Product.is_active == True)

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    query = query.order_by(Product.id.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    products = result.scalars().all()
    return products


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
