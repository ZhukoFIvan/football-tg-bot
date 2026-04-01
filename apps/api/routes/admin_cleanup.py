"""
Административный endpoint для очистки неиспользуемых изображений и медиа-менеджер
"""
import json
from datetime import datetime
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from core.db.session import get_db
from core.db.models import Section, Category, Product, Banner, User
from core.dependencies import get_admin_user

router = APIRouter()

SUBFOLDERS = ["sections", "categories", "products", "banners"]


async def _collect_used_images(db: AsyncSession) -> Set[str]:
    """Collect all image paths referenced in the database (normalized without leading slash)."""
    used: Set[str] = set()

    sections_result = await db.execute(select(Section))
    for section in sections_result.scalars().all():
        if section.image:
            used.add(section.image.lstrip("/"))

    categories_result = await db.execute(select(Category))
    for cat in categories_result.scalars().all():
        if cat.main_image:
            used.add(cat.main_image.lstrip("/"))
        if cat.additional_image:
            used.add(cat.additional_image.lstrip("/"))

    products_result = await db.execute(select(Product))
    for product in products_result.scalars().all():
        if product.images:
            try:
                for img in json.loads(product.images):
                    used.add(img.lstrip("/"))
            except Exception:
                pass

    banners_result = await db.execute(select(Banner))
    for banner in banners_result.scalars().all():
        if banner.image:
            used.add(banner.image.lstrip("/"))

    return used


@router.get("/media")
async def list_media_files(
    subfolder: Optional[str] = Query(None, description="Filter by subfolder: sections, categories, products, banners"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """List all uploaded media files with usage info."""
    uploads_base = Path("uploads")
    if not uploads_base.exists():
        return {"items": [], "total": 0, "total_size_mb": 0, "unused_count": 0}

    used_images = await _collect_used_images(db)

    folders = [subfolder] if subfolder and subfolder in SUBFOLDERS else SUBFOLDERS
    items = []
    total_size = 0
    unused_count = 0

    for folder in folders:
        folder_path = uploads_base / folder
        if not folder_path.exists():
            continue

        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            stat = file_path.stat()
            relative = f"uploads/{folder}/{file_path.name}"
            is_used = relative in used_images
            total_size += stat.st_size
            if not is_used:
                unused_count += 1
            items.append({
                "path": f"/{relative}",
                "filename": file_path.name,
                "subfolder": folder,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_used": is_used,
            })

    items.sort(key=lambda x: x["modified_at"], reverse=True)

    return {
        "items": items,
        "total": len(items),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "unused_count": unused_count,
    }


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
    used_images = await _collect_used_images(db)

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

    for sf in SUBFOLDERS:
        folder_path = uploads_base / sf
        if not folder_path.exists():
            continue

        for file_path in folder_path.iterdir():
            if file_path.is_file():
                relative_path = f"uploads/{sf}/{file_path.name}"
                if relative_path not in used_images:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files.append(relative_path)
                    total_freed_size += file_size

    freed_space_mb = round(total_freed_size / (1024 * 1024), 2)

    return {
        "ok": True,
        "deleted_count": len(deleted_files),
        "freed_space_mb": freed_space_mb,
        "deleted_files": deleted_files[:50]
    }


@router.get("/cleanup/stats")
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Статистика по использованию дискового пространства."""
    uploads_base = Path("uploads")
    if not uploads_base.exists():
        return {"total_files": 0, "total_size_mb": 0, "by_folder": {}}

    stats = {"total_files": 0, "total_size_mb": 0, "by_folder": {}}

    for sf in SUBFOLDERS:
        folder_path = uploads_base / sf
        if not folder_path.exists():
            continue

        folder_files = 0
        folder_size = 0
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                folder_files += 1
                folder_size += file_path.stat().st_size

        stats["by_folder"][sf] = {
            "files": folder_files,
            "size_mb": round(folder_size / (1024 * 1024), 2),
        }
        stats["total_files"] += folder_files
        stats["total_size_mb"] += folder_size

    stats["total_size_mb"] = round(stats["total_size_mb"] / (1024 * 1024), 2)

    sections_count = await db.scalar(select(func.count(Section.id)))
    categories_count = await db.scalar(select(func.count(Category.id)))
    products_count = await db.scalar(select(func.count(Product.id)))
    banners_count = await db.scalar(select(func.count(Banner.id)))

    stats["database"] = {
        "sections": sections_count,
        "categories": categories_count,
        "products": products_count,
        "banners": banners_count,
    }

    return stats


class DeleteMediaRequest(BaseModel):
    paths: List[str]


@router.delete("/media")
async def delete_media_files(
    body: DeleteMediaRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Bulk-delete media files and clean up DB references to them."""
    if not body.paths:
        return {"ok": True, "deleted_count": 0, "freed_space_mb": 0}

    paths_to_delete = {p.lstrip("/") for p in body.paths}

    total_freed = 0
    deleted_count = 0
    for norm_path in paths_to_delete:
        full = Path(norm_path)
        if full.exists() and full.is_file():
            total_freed += full.stat().st_size
            full.unlink()
            deleted_count += 1

    # Clean DB references so entities don't point to deleted files
    sections_result = await db.execute(select(Section))
    for section in sections_result.scalars().all():
        if section.image and section.image.lstrip("/") in paths_to_delete:
            section.image = None

    categories_result = await db.execute(select(Category))
    for cat in categories_result.scalars().all():
        if cat.main_image and cat.main_image.lstrip("/") in paths_to_delete:
            cat.main_image = None
        if cat.additional_image and cat.additional_image.lstrip("/") in paths_to_delete:
            cat.additional_image = None

    products_result = await db.execute(select(Product))
    for product in products_result.scalars().all():
        if not product.images:
            continue
        try:
            images_list = json.loads(product.images)
            filtered = [img for img in images_list if img.lstrip("/") not in paths_to_delete]
            if len(filtered) != len(images_list):
                product.images = json.dumps(filtered)
        except Exception:
            pass

    banners_result = await db.execute(select(Banner))
    for banner in banners_result.scalars().all():
        if banner.image and banner.image.lstrip("/") in paths_to_delete:
            banner.image = None

    await db.commit()

    return {
        "ok": True,
        "deleted_count": deleted_count,
        "freed_space_mb": round(total_freed / (1024 * 1024), 2),
    }
