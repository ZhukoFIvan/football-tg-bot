"""
Публичные эндпоинты для баннеров и бейджей
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.db.session import get_db
from core.db.models import Banner, Badge

router = APIRouter()


class BannerResponse(BaseModel):
    id: int
    title: str
    description: str | None
    image: str
    link: str | None
    sort_order: int

    class Config:
        from_attributes = True


class BadgeResponse(BaseModel):
    id: int
    title: str
    color: str
    text_color: str

    class Config:
        from_attributes = True


@router.get("/banners", response_model=List[BannerResponse])
async def get_banners(db: AsyncSession = Depends(get_db)):
    """Получить активные баннеры для главной страницы"""
    result = await db.execute(
        select(Banner)
        .where(Banner.is_active == True)
        .order_by(Banner.sort_order, Banner.id)
    )
    return result.scalars().all()


@router.get("/badges", response_model=List[BadgeResponse])
async def get_badges(db: AsyncSession = Depends(get_db)):
    """Получить все активные бейджи"""
    result = await db.execute(
        select(Badge)
        .where(Badge.is_active == True)
        .order_by(Badge.id)
    )
    return result.scalars().all()
