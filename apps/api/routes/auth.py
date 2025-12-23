"""
Авторизация через Telegram WebApp
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.db.session import get_db
from core.db.models import User
from core.auth import verify_telegram_webapp_data, create_jwt_token
from core.config import settings

router = APIRouter()


class TelegramAuthRequest(BaseModel):
    """Запрос на авторизацию с initData от Telegram WebApp"""
    initData: str


class AuthResponse(BaseModel):
    """Ответ с JWT токеном"""
    ok: bool
    access_token: str
    user_id: int
    telegram_id: int
    is_admin: bool  # Флаг администратора


class DevAuthRequest(BaseModel):
    """Запрос на получение dev токена"""
    telegram_id: int


@router.post("/dev-token", response_model=AuthResponse)
async def dev_token(
    request: DevAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    🔧 DEV ONLY: Получить токен для разработки без Telegram WebApp

    Используйте telegram_id из OWNER_TG_IDS для получения админ-токена
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    telegram_id = request.telegram_id

    # Ищем или создаем пользователя
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Создаем тестового пользователя
        is_admin = telegram_id in settings.owner_ids
        user = User(
            telegram_id=telegram_id,
            username=f"test_user_{telegram_id}",
            first_name="Test",
            last_name="User",
            is_admin=is_admin
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Генерируем JWT токен
    token = create_jwt_token(telegram_id=user.telegram_id, user_id=user.id)

    return AuthResponse(
        ok=True,
        access_token=token,
        user_id=user.id,
        telegram_id=user.telegram_id,
        is_admin=user.is_admin
    )


@router.post("/telegram", response_model=AuthResponse)
async def telegram_auth(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Авторизация через Telegram WebApp initData

    1. Проверяет валидность initData
    2. Создает или находит пользователя в БД
    3. Возвращает JWT токен
    """
    # Проверяем initData
    user_data = verify_telegram_webapp_data(request.initData)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID not found")

    # Ищем или создаем пользователя
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Создаем нового пользователя
        user = User(
            telegram_id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Обновляем данные существующего пользователя
        user.username = user_data.get("username")
        user.first_name = user_data.get("first_name")
        user.last_name = user_data.get("last_name")
        await db.commit()

    # Проверяем бан
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    # Генерируем JWT токен
    token = create_jwt_token(telegram_id=user.telegram_id, user_id=user.id)

    return AuthResponse(
        ok=True,
        access_token=token,
        user_id=user.id,
        telegram_id=user.telegram_id,
        is_admin=user.is_admin
    )
