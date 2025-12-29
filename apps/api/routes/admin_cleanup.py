"""
Административный endpoint для очистки неиспользуемых изображений
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path
import os

from core.db.session import get_db
from core.db.models import Section, Category, Product, Banner, User
from core.dependencies import get_admin_user

router = APIRouter()


@router.post("/cleanup/unused-images")
async def cleanup_unused_images(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Удалить неиспользуемые изображения из uploads/

    Сканирует все папки uploads/* и удаляет файлы,
    которые не привязаны ни к одной записи в БД
    """
    import json

    # Собрать все используемые пути из БД
    used_images = set()

    # 1. Изображения секций
    sections_result = await db.execute(select(Section))
    for section in sections_result.scalars().all():
        if section.image:
            used_images.add(section.image)

    # 2. Изображения категорий
    categories_result = await db.execute(select(Category))
    for category in categories_result.scalars().all():
        if category.main_image:
            used_images.add(category.main_image)
        if category.additional_image:
            used_images.add(category.additional_image)

    # 3. Изображения товаров (массив JSON)
    products_result = await db.execute(select(Product))
    for product in products_result.scalars().all():
        if product.images:
            try:
                images_list = json.loads(product.images)
                for img in images_list:
                    used_images.add(img)
            except:
                pass

    # 4. Изображения баннеров
    banners_result = await db.execute(select(Banner))
    for banner in banners_result.scalars().all():
        if banner.image:
            used_images.add(banner.image)

    # Сканировать директории uploads
    deleted_files = []
    total_freed_size = 0

    uploads_base = Path("uploads")
    if not uploads_base.exists():
        return {
            "ok": True,
            "deleted_count": 0,
            "freed_space_mb": 0,
            "deleted_files": []
        }

    # Пройтись по всем поддиректориям
    for subfolder in ["sections", "categories", "products", "banners"]:
        folder_path = uploads_base / subfolder
        if not folder_path.exists():
            continue

        for file_path in folder_path.iterdir():
            if file_path.is_file():
                # Относительный путь (как в БД)
                relative_path = f"uploads/{subfolder}/{file_path.name}"

                # Если файл не используется - удалить
                if relative_path not in used_images:
                    file_size = file_path.stat().st_size
                    file_path.unlink()  # Удалить файл
                    deleted_files.append(relative_path)
                    total_freed_size += file_size

    freed_space_mb = round(total_freed_size / (1024 * 1024), 2)

    return {
        "ok": True,
        "deleted_count": len(deleted_files),
        "freed_space_mb": freed_space_mb,
        "deleted_files": deleted_files[:50]  # Показать первые 50
    }


@router.get("/cleanup/stats")
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Статистика по использованию дискового пространства
    """
    import json

    uploads_base = Path("uploads")
    if not uploads_base.exists():
        return {
            "total_files": 0,
            "total_size_mb": 0,
            "by_folder": {}
        }

    stats = {
        "total_files": 0,
        "total_size_mb": 0,
        "by_folder": {}
    }

    for subfolder in ["sections", "categories", "products", "banners"]:
        folder_path = uploads_base / subfolder
        if not folder_path.exists():
            continue

        folder_files = 0
        folder_size = 0

        for file_path in folder_path.iterdir():
            if file_path.is_file():
                folder_files += 1
                folder_size += file_path.stat().st_size

        stats["by_folder"][subfolder] = {
            "files": folder_files,
            "size_mb": round(folder_size / (1024 * 1024), 2)
        }

        stats["total_files"] += folder_files
        stats["total_size_mb"] += folder_size

    stats["total_size_mb"] = round(stats["total_size_mb"] / (1024 * 1024), 2)

    # Получить количество записей в БД
    sections_count = await db.scalar(select(func.count(Section.id)))
    categories_count = await db.scalar(select(func.count(Category.id)))
    products_count = await db.scalar(select(func.count(Product.id)))
    banners_count = await db.scalar(select(func.count(Banner.id)))

    from sqlalchemy import func
    stats["database"] = {
        "sections": sections_count,
        "categories": categories_count,
        "products": products_count,
        "banners": banners_count
    }

    return stats

