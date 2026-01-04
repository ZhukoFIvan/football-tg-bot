"""
Административные эндпоинты для модерации отзывов
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel
from datetime import datetime

from core.db.session import get_db
from core.db.models import Review, Product, User
from core.dependencies import get_admin_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class ReviewUserInfo(BaseModel):
    """Информация о пользователе в отзыве"""
    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class ProductInfo(BaseModel):
    """Информация о товаре"""
    id: int
    title: str
    slug: str

    class Config:
        from_attributes = True


class AdminReviewResponse(BaseModel):
    """Отзыв для админ-панели"""
    id: int
    product_id: int
    product: ProductInfo
    user: ReviewUserInfo
    rating: int
    comment: Optional[str] = None
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReviewModerationAction(BaseModel):
    """Действие модерации"""
    action: str  # "approve" или "reject"


# ==================== ENDPOINTS ====================

@router.get("/reviews", response_model=List[AdminReviewResponse])
async def admin_get_reviews(
    status: Optional[str] = None,  # pending, approved, rejected
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить все отзывы для модерации
    Можно фильтровать по статусу
    """
    query = select(Review)

    if status:
        if status not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        query = query.where(Review.status == status)

    query = query.order_by(Review.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    reviews = result.scalars().all()

    # Загрузить пользователей и товары
    if reviews:
        user_ids = [review.user_id for review in reviews]
        product_ids = [review.product_id for review in reviews]

        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_dict = {user.id: user for user in users_result.scalars().all()}

        products_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products_dict = {
            product.id: product for product in products_result.scalars().all()}

        # Привязать к отзывам
        for review in reviews:
            review.user = users_dict.get(review.user_id)
            review.product = products_dict.get(review.product_id)

    return [
        AdminReviewResponse(
            id=review.id,
            product_id=review.product_id,
            product=ProductInfo(
                id=review.product.id,
                title=review.product.title,
                slug=review.product.slug
            ) if review.product else None,
            user=ReviewUserInfo.from_orm(
                review.user) if review.user else None,
            rating=review.rating,
            comment=review.comment,
            status=review.status,
            created_at=review.created_at.isoformat(),
            updated_at=review.updated_at.isoformat()
        )
        for review in reviews
    ]


@router.get("/reviews/stats")
async def admin_get_review_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Получить статистику по отзывам
    """
    # Посчитать количество отзывов по статусам
    stats_result = await db.execute(
        select(Review.status, func.count(Review.id))
        .group_by(Review.status)
    )
    stats_dict = {row[0]: row[1] for row in stats_result.all()}

    return {
        "pending": stats_dict.get("pending", 0),
        "approved": stats_dict.get("approved", 0),
        "rejected": stats_dict.get("rejected", 0),
        "total": sum(stats_dict.values())
    }


@router.patch("/reviews/{review_id}/moderate")
async def admin_moderate_review(
    review_id: int,
    action: ReviewModerationAction,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Модерировать отзыв (одобрить или отклонить)
    """
    if action.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=400, detail="Action must be 'approve' or 'reject'")

    # Получить отзыв
    review_result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Обновить статус
    if action.action == "approve":
        review.status = "approved"
    else:
        review.status = "rejected"

    await db.commit()

    # Обновить рейтинг товара (пересчитать с учетом нового статуса)
    from apps.api.routes.reviews import update_product_rating
    await update_product_rating(db, review.product_id)
    await db.commit()

    await db.refresh(review)

    return {"ok": True, "review_id": review.id, "new_status": review.status}


@router.delete("/reviews/{review_id}")
async def admin_delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Удалить отзыв (админ может удалять любые отзывы)
    """
    review_result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    product_id = review.product_id

    await db.delete(review)
    await db.commit()

    # Обновить рейтинг товара
    from apps.api.routes.reviews import update_product_rating
    await update_product_rating(db, product_id)
    await db.commit()

    return {"ok": True, "message": "Review deleted successfully"}
