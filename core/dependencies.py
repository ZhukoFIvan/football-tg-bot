"""
FastAPI dependencies для авторизации и проверки прав
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.auth import verify_jwt_token
from core.db.session import get_db
from core.db.models import User
from core.config import settings


async def get_current_user_payload(authorization: str = Header(None)) -> dict:
    """
    Получить payload текущего пользователя из JWT токена
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получить объект текущего пользователя из БД
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверить что текущий пользователь - администратор
    Проверяет либо флаг is_admin в БД, либо наличие в OWNER_TG_IDS
    """
    # Проверяем флаг is_admin
    if current_user.is_admin:
        return current_user

    # Проверяем наличие в списке владельцев
    if current_user.telegram_id in settings.owner_ids:
        # Автоматически устанавливаем флаг is_admin если пользователь в OWNER_TG_IDS
        current_user.is_admin = True
        return current_user

    raise HTTPException(
        status_code=403,
        detail="Admin access required"
    )
