"""
Эндпоинты для системы отзывов (отзывы относятся ко всему магазину, а не к конкретным товарам)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel, Field
from decimal import Decimal

from core.db.session import get_db
from core.db.models import Review, User
from core.dependencies import get_current_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5 звезд")
    comment: Optional[str] = Field(
        None, max_length=1000, description="Текст отзыва")


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class ReviewUserInfo(BaseModel):
    """Информация о пользователе в отзыве"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def display_name(self) -> str:
        """Отображаемое имя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        return f"Пользователь {self.id}"


class ReviewResponse(BaseModel):
    id: int
    user: ReviewUserInfo
    rating: int
    comment: Optional[str] = None
    created_at: str
    updated_at: str
    is_own: bool = False  # Флаг: это отзыв текущего пользователя
    status: Optional[str] = None  # Статус отзыва (показывается только для собственных неодобренных отзывов)

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_user(cls, review: Review, current_user_id: Optional[int] = None):
        """Создать response с информацией о пользователе"""
        is_own = (current_user_id == review.user_id) if current_user_id else False
        # Показывать статус только для собственных отзывов, которые не одобрены
        status = None
        if is_own and review.status != "approved":
            status = review.status

        return cls(
            id=review.id,
            user=ReviewUserInfo.from_orm(review.user),
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at.isoformat(),
            updated_at=review.updated_at.isoformat(),
            is_own=is_own,
            status=status
        )


class ShopRatingInfo(BaseModel):
    """Статистика рейтинга магазина"""
    average_rating: float
    reviews_count: int
    rating_distribution: dict  # {5: 10, 4: 5, 3: 2, 2: 1, 1: 0}


# ==================== ENDPOINTS ====================

@router.get("/reviews", response_model=List[ReviewResponse])
async def get_shop_reviews(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получить отзывы на магазин
    Показывает одобренные отзывы для всех + собственные отзывы пользователя (любого статуса)
    """
    # Получить одобренные отзывы и собственные отзывы пользователя (если авторизован)
    if current_user:
        # Получить одобренные отзывы ИЛИ собственные отзывы текущего пользователя
        reviews_result = await db.execute(
            select(Review)
            .where(
                or_(
                    Review.status == "approved",
                    Review.user_id == current_user.id
                )
            )
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    else:
        # Для неавторизованных - только одобренные отзывы
        reviews_result = await db.execute(
            select(Review)
            .where(Review.status == "approved")
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

    reviews = reviews_result.scalars().all()

    # Загрузить пользователей для отзывов
    user_ids = [review.user_id for review in reviews]
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_dict = {user.id: user for user in users_result.scalars().all()}

        # Привязать пользователей к отзывам
        for review in reviews:
            review.user = users_dict.get(review.user_id)

    current_user_id = current_user.id if current_user else None
    return [ReviewResponse.from_orm_with_user(review, current_user_id) for review in reviews]


@router.get("/shop/rating", response_model=ShopRatingInfo)
async def get_shop_rating(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику рейтинга магазина
    """
    # Пересчитать статистику напрямую из таблицы reviews (только одобренные)
    stats_result = await db.execute(
        select(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('count')
        )
        .where(Review.status == "approved")
    )
    stats = stats_result.first()

    # Вычислить средний рейтинг и количество отзывов
    if stats.avg_rating is not None:
        average_rating = round(float(stats.avg_rating), 2)
        reviews_count = stats.count
    else:
        average_rating = 0.0
        reviews_count = 0

    # Получить распределение рейтингов (только одобренные)
    rating_dist_result = await db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.status == "approved")
        .group_by(Review.rating)
    )
    rating_distribution = {row[0]: row[1] for row in rating_dist_result.all()}

    # Заполнить пропущенные рейтинги нулями
    for i in range(1, 6):
        if i not in rating_distribution:
            rating_distribution[i] = 0

    return ShopRatingInfo(
        average_rating=average_rating,
        reviews_count=reviews_count,
        rating_distribution=rating_distribution
    )


@router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать отзыв на магазин

    Требуется авторизация
    Каждый пользователь может оставить только один отзыв на магазин
    """
    # Проверить что пользователь еще не оставлял отзыв на магазин
    existing_review_result = await db.execute(
        select(Review).where(Review.user_id == current_user.id)
    )
    existing_review = existing_review_result.scalar_one_or_none()
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this shop. Use PUT to update your review."
        )

    # Создать отзыв (со статусом pending - ожидает модерации)
    review = Review(
        user_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment,
        status="pending"
    )
    db.add(review)

    await db.commit()
    await db.refresh(review)

    # Загрузить пользователя
    review.user = current_user

    return ReviewResponse.from_orm_with_user(review, current_user.id)


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить свой отзыв на магазин

    Требуется авторизация
    """
    # Получить отзыв
    review_result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Проверить что это отзыв текущего пользователя
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only update your own reviews")

    # Обновить поля
    if review_data.rating is not None:
        review.rating = review_data.rating
    if review_data.comment is not None:
        review.comment = review_data.comment

    # После редактирования отзыв снова отправляется на модерацию
    review.status = "pending"

    await db.commit()
    await db.refresh(review)

    # Загрузить пользователя
    review.user = current_user

    return ReviewResponse.from_orm_with_user(review, current_user.id)


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить свой отзыв на магазин

    Требуется авторизация
    """
    # Получить отзыв
    review_result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Проверить что это отзыв текущего пользователя
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own reviews")

    # Удалить отзыв
    await db.delete(review)

    await db.commit()

    return {"ok": True, "message": "Review deleted successfully"}

