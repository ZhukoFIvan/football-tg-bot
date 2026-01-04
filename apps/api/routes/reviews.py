"""
Эндпоинты для системы отзывов
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field
from decimal import Decimal

from core.db.session import get_db
from core.db.models import Review, Product, User
from core.dependencies import get_current_user

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class ReviewCreate(BaseModel):
    product_id: int
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
    product_id: int
    user: ReviewUserInfo
    rating: int
    comment: Optional[str] = None
    created_at: str
    updated_at: str
    is_own: bool = False  # Флаг: это отзыв текущего пользователя

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_user(cls, review: Review, current_user_id: Optional[int] = None):
        """Создать response с информацией о пользователе"""
        return cls(
            id=review.id,
            product_id=review.product_id,
            user=ReviewUserInfo.from_orm(review.user),
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at.isoformat(),
            updated_at=review.updated_at.isoformat(),
            is_own=(current_user_id ==
                    review.user_id) if current_user_id else False
        )


class ProductRatingInfo(BaseModel):
    """Статистика рейтинга товара"""
    average_rating: float
    reviews_count: int
    rating_distribution: dict  # {5: 10, 4: 5, 3: 2, 2: 1, 1: 0}


# ==================== ENDPOINTS ====================

@router.get("/products/{product_id}/reviews", response_model=List[ReviewResponse])
async def get_product_reviews(
    product_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получить отзывы на товар
    """
    # Проверить существование товара
    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Получить только одобренные отзывы
    reviews_result = await db.execute(
        select(Review)
        .where(
            and_(
                Review.product_id == product_id,
                Review.status == "approved"
            )
        )
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


@router.get("/products/{product_id}/rating", response_model=ProductRatingInfo)
async def get_product_rating(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику рейтинга товара
    """
    # Проверить существование товара
    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Пересчитать статистику напрямую из таблицы reviews (только одобренные)
    stats_result = await db.execute(
        select(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('count')
        )
        .where(
            and_(
                Review.product_id == product_id,
                Review.status == "approved"
            )
        )
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
        .where(
            and_(
                Review.product_id == product_id,
                Review.status == "approved"
            )
        )
        .group_by(Review.rating)
    )
    rating_distribution = {row[0]: row[1] for row in rating_dist_result.all()}

    # Заполнить пропущенные рейтинги нулями
    for i in range(1, 6):
        if i not in rating_distribution:
            rating_distribution[i] = 0

    return ProductRatingInfo(
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
    Создать отзыв на товар

    Требуется авторизация
    """
    # Проверить существование товара
    product_result = await db.execute(
        select(Product).where(Product.id == review_data.product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Проверить что пользователь еще не оставлял отзыв на этот товар
    existing_review_result = await db.execute(
        select(Review).where(
            and_(
                Review.product_id == review_data.product_id,
                Review.user_id == current_user.id
            )
        )
    )
    existing_review = existing_review_result.scalar_one_or_none()
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this product. Use PUT to update your review."
        )

    # Создать отзыв (со статусом pending - ожидает модерации)
    review = Review(
        product_id=review_data.product_id,
        user_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment,
        status="pending"
    )
    db.add(review)

    # Обновить рейтинг товара
    await update_product_rating(db, review_data.product_id)

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
    Обновить свой отзыв

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

    # Обновить рейтинг товара
    await update_product_rating(db, review.product_id)

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
    Удалить свой отзыв

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

    product_id = review.product_id

    # Удалить отзыв
    await db.delete(review)

    # Обновить рейтинг товара
    await update_product_rating(db, product_id)

    await db.commit()

    return {"ok": True, "message": "Review deleted successfully"}


# ==================== HELPER FUNCTIONS ====================

async def update_product_rating(db: AsyncSession, product_id: int):
    """
    Обновить средний рейтинг и количество отзывов у товара (только одобренные)
    """
    # Посчитать средний рейтинг и количество отзывов (только одобренные)
    stats_result = await db.execute(
        select(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('count')
        )
        .where(
            and_(
                Review.product_id == product_id,
                Review.status == "approved"
            )
        )
    )
    stats = stats_result.first()

    # Обновить товар
    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one()

    if stats.avg_rating is not None:
        product.average_rating = Decimal(
            str(round(float(stats.avg_rating), 2)))
        product.reviews_count = stats.count
    else:
        product.average_rating = Decimal('0')
        product.reviews_count = 0

