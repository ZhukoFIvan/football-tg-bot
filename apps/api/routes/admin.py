"""
Административные эндпоинты для управления контентом
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from decimal import Decimal
import json

from core.db.session import get_db
from core.db.models import (
    Section, Category, Product, Badge, Banner, User, Order
)
from core.dependencies import get_admin_user
from core.storage import save_upload_file, delete_file

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class SectionCreate(BaseModel):
    name: str
    route: Optional[str] = None
    # время до окончания в секундах (конвертируется в end_time)
    rest_time: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    route: Optional[str] = None
    # время до окончания в секундах (конвертируется в end_time)
    rest_time: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryCreate(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductCreate(BaseModel):
    category_id: int
    section_id: Optional[int] = None
    badge_id: Optional[int] = None  # Один бейдж
    title: str
    slug: str
    description: Optional[str] = None
    price: Decimal
    old_price: Optional[Decimal] = None
    promotion_text: Optional[str] = None  # Текст акции (например "Скидка 50%")
    currency: str = "RUB"
    stock_count: int = 0
    is_active: bool = True


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    section_id: Optional[int] = None
    badge_id: Optional[int] = None  # Один бейдж
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    old_price: Optional[Decimal] = None
    promotion_text: Optional[str] = None  # Текст акции
    currency: Optional[str] = None
    stock_count: Optional[int] = None
    is_active: Optional[bool] = None


class BadgeCreate(BaseModel):
    title: str
    color: str = "#FF5722"
    text_color: str = "#FFFFFF"
    is_active: bool = True


class BadgeUpdate(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    text_color: Optional[str] = None
    is_active: Optional[bool] = None


class BannerCreate(BaseModel):
    title: str
    description: Optional[str] = None
    link: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


# ==================== SECTIONS ====================

@router.get("/sections")
async def admin_get_sections(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить все разделы (включая неактивные)"""
    result = await db.execute(
        select(Section).order_by(Section.sort_order, Section.id)
    )
    return result.scalars().all()


@router.post("/sections")
async def admin_create_section(
    data: SectionCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Создать новый раздел"""
    from datetime import datetime, timedelta

    section_data = data.model_dump()

    # Конвертировать rest_time в end_time
    if section_data.get('rest_time'):
        section_data['end_time'] = datetime.utcnow(
        ) + timedelta(seconds=section_data['rest_time'])
        del section_data['rest_time']

    section = Section(**section_data)
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return section


@router.patch("/sections/{section_id}")
async def admin_update_section(
    section_id: int,
    data: SectionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Обновить раздел"""
    from datetime import datetime, timedelta

    result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = data.model_dump(exclude_unset=True)

    # Конвертировать rest_time в end_time
    if 'rest_time' in update_data:
        if update_data['rest_time'] is not None:
            update_data['end_time'] = datetime.utcnow(
            ) + timedelta(seconds=update_data['rest_time'])
        else:
            update_data['end_time'] = None
        del update_data['rest_time']

    for key, value in update_data.items():
        setattr(section, key, value)

    await db.commit()
    await db.refresh(section)
    return section


@router.delete("/sections/{section_id}")
async def admin_delete_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить раздел"""
    result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Удалить связанное изображение
    if section.image:
        delete_file(section.image)

    await db.delete(section)
    await db.commit()
    return {"ok": True, "message": "Section deleted"}


@router.post("/sections/{section_id}/image")
async def admin_upload_section_image(
    section_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Загрузить изображение для секции"""
    result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Удалить старое изображение
    if section.image:
        delete_file(section.image)

    # Сохранить новое
    file_path = await save_upload_file(file, subfolder="sections")
    section.image = file_path

    await db.commit()
    await db.refresh(section)
    return {"ok": True, "path": file_path}


# ==================== CATEGORIES ====================

@router.get("/categories")
async def admin_get_categories(
    section_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить все категории"""
    query = select(Category)

    if section_id is not None:
        query = query.where(Category.section_id == section_id)

    query = query.order_by(Category.sort_order, Category.id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/categories")
async def admin_create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Создать новую категорию"""
    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch("/categories/{category_id}")
async def admin_update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Обновить категорию"""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}")
async def admin_delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить категорию"""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Удалить изображение
    if category.image:
        delete_file(category.image)

    await db.delete(category)
    await db.commit()
    return {"ok": True, "message": "Category deleted"}


@router.post("/categories/{category_id}/main-image")
async def admin_upload_category_main_image(
    category_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Загрузить основное изображение для категории"""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Удалить старое изображение
    if category.main_image:
        delete_file(category.main_image)

    # Сохранить новое
    file_path = await save_upload_file(file, subfolder="categories")
    category.main_image = file_path

    await db.commit()
    await db.refresh(category)
    return {"ok": True, "path": file_path}


@router.post("/categories/{category_id}/additional-image")
async def admin_upload_category_additional_image(
    category_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Загрузить дополнительное изображение для категории"""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Удалить старое изображение
    if category.additional_image:
        delete_file(category.additional_image)

    # Сохранить новое
    file_path = await save_upload_file(file, subfolder="categories")
    category.additional_image = file_path

    await db.commit()
    await db.refresh(category)
    return {"ok": True, "path": file_path}


# ==================== PRODUCTS ====================

@router.get("/products")
async def admin_get_products(
    category_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить все товары"""
    query = select(Product)

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    query = query.order_by(Product.id.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/products")
async def admin_create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Создать новый товар"""
    product = Product(**data.model_dump())
    product.images = "[]"  # Пустой массив изображений

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/products/{product_id}")
async def admin_update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Обновить товар"""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновить поля
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить товар"""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Удалить изображение
    if product.image:
        delete_file(product.image)

    await db.delete(product)
    await db.commit()
    return {"ok": True, "message": "Product deleted"}


@router.post("/products/{product_id}/images")
async def admin_upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Загрузить изображения для товара (множественная загрузка)"""
    import json

    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Получить текущие изображения
    current_images = []
    if product.images:
        try:
            current_images = json.loads(product.images)
        except:
            current_images = []

    # Сохранить новые изображения
    new_images = []
    for file in files:
        file_path = await save_upload_file(file, subfolder="products")
        new_images.append(file_path)

    # Добавить к существующим
    all_images = current_images + new_images
    product.images = json.dumps(all_images)

    await db.commit()
    await db.refresh(product)
    return {"ok": True, "images": all_images}


@router.delete("/products/{product_id}/images/{image_index}")
async def admin_delete_product_image(
    product_id: int,
    image_index: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить изображение товара по индексу"""
    import json

    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Получить текущие изображения
    current_images = []
    if product.images:
        try:
            current_images = json.loads(product.images)
        except:
            current_images = []

    if image_index < 0 or image_index >= len(current_images):
        raise HTTPException(status_code=404, detail="Image not found")

    # Удалить файл
    image_path = current_images[image_index]
    delete_file(image_path)

    # Удалить из массива
    current_images.pop(image_index)
    product.images = json.dumps(current_images)

    await db.commit()
    await db.refresh(product)
    return {"ok": True, "images": current_images}


# ==================== BADGES ====================

@router.get("/badges")
async def admin_get_badges(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить все бейджи"""
    result = await db.execute(select(Badge).order_by(Badge.id))
    return result.scalars().all()


@router.post("/badges")
async def admin_create_badge(
    data: BadgeCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Создать новый бейдж"""
    badge = Badge(**data.model_dump())
    db.add(badge)
    await db.commit()
    await db.refresh(badge)
    return badge


@router.patch("/badges/{badge_id}")
async def admin_update_badge(
    badge_id: int,
    data: BadgeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Обновить бейдж"""
    result = await db.execute(
        select(Badge).where(Badge.id == badge_id)
    )
    badge = result.scalar_one_or_none()

    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(badge, key, value)

    await db.commit()
    await db.refresh(badge)
    return badge


@router.delete("/badges/{badge_id}")
async def admin_delete_badge(
    badge_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить бейдж"""
    result = await db.execute(
        select(Badge).where(Badge.id == badge_id)
    )
    badge = result.scalar_one_or_none()

    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    await db.delete(badge)
    await db.commit()
    return {"ok": True, "message": "Badge deleted"}


# ==================== BANNERS ====================

@router.get("/banners")
async def admin_get_banners(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Получить все баннеры"""
    result = await db.execute(
        select(Banner).order_by(Banner.sort_order, Banner.id)
    )
    return result.scalars().all()


@router.post("/banners")
async def admin_create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Создать новый баннер"""
    banner = Banner(**data.model_dump())
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return banner


@router.patch("/banners/{banner_id}")
async def admin_update_banner(
    banner_id: int,
    data: BannerUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Обновить баннер"""
    result = await db.execute(
        select(Banner).where(Banner.id == banner_id)
    )
    banner = result.scalar_one_or_none()

    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(banner, key, value)

    await db.commit()
    await db.refresh(banner)
    return banner


@router.delete("/banners/{banner_id}")
async def admin_delete_banner(
    banner_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Удалить баннер"""
    result = await db.execute(
        select(Banner).where(Banner.id == banner_id)
    )
    banner = result.scalar_one_or_none()

    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")

    # Удалить изображение
    if banner.image:
        delete_file(banner.image)

    await db.delete(banner)
    await db.commit()
    return {"ok": True, "message": "Banner deleted"}


@router.post("/banners/{banner_id}/image")
async def admin_upload_banner_image(
    banner_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Загрузить изображение для баннера"""
    result = await db.execute(
        select(Banner).where(Banner.id == banner_id)
    )
    banner = result.scalar_one_or_none()

    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")

    # Удалить старое изображение
    if banner.image:
        delete_file(banner.image)

    # Сохранить новое
    file_path = await save_upload_file(file, subfolder="banners")
    banner.image = file_path

    await db.commit()
    await db.refresh(banner)
    return {"ok": True, "path": file_path}
