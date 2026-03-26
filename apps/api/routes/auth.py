"""
Авторизация: Telegram WebApp, Telegram Login Widget, логин/регистрация по email+паролю
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from core.db.session import get_db
from core.db.models import User
from core.auth import (
    verify_telegram_webapp_data,
    verify_telegram_widget_data,
    create_jwt_token,
    hash_password,
    verify_password,
)
from core.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Схемы запросов/ответов
# ---------------------------------------------------------------------------

class TelegramAuthRequest(BaseModel):
    initData: str


class TelegramWidgetAuthRequest(BaseModel):
    """Данные от Telegram Login Widget (id, first_name, hash, auth_date, ...)"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class RegisterRequest(BaseModel):
    display_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """Вход по email или display_name + пароль"""
    login: str   # email или display_name
    password: str


class AuthResponse(BaseModel):
    ok: bool
    access_token: str
    user_id: int
    telegram_id: Optional[int] = None
    is_admin: bool
    display_name: Optional[str] = None


class DevAuthRequest(BaseModel):
    telegram_id: int


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _build_response(user: User, token: str) -> AuthResponse:
    name = user.display_name or user.first_name or user.username
    return AuthResponse(
        ok=True,
        access_token=token,
        user_id=user.id,
        telegram_id=user.telegram_id,
        is_admin=user.is_admin,
        display_name=name,
    )


# ---------------------------------------------------------------------------
# DEV endpoint
# ---------------------------------------------------------------------------

@router.post("/dev-token", response_model=AuthResponse)
async def dev_token(
    request: DevAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    🔧 DEV ONLY: Получить токен для разработки без Telegram WebApp
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    telegram_id = request.telegram_id

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
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

    token = create_jwt_token(user_id=user.id, telegram_id=user.telegram_id)
    return _build_response(user, token)


# ---------------------------------------------------------------------------
# Telegram WebApp (Mini App)
# ---------------------------------------------------------------------------

@router.post("/telegram", response_model=AuthResponse)
async def telegram_auth(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Авторизация через Telegram WebApp initData (Mini App)
    """
    user_data = verify_telegram_webapp_data(request.initData)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID not found")

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
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
        user.username = user_data.get("username")
        user.first_name = user_data.get("first_name")
        user.last_name = user_data.get("last_name")
        await db.commit()

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    token = create_jwt_token(user_id=user.id, telegram_id=user.telegram_id)
    return _build_response(user, token)


# ---------------------------------------------------------------------------
# Telegram Login Widget (сайт)
# ---------------------------------------------------------------------------

@router.post("/telegram-widget", response_model=AuthResponse)
async def telegram_widget_auth(
    request: TelegramWidgetAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Авторизация через Telegram Login Widget на сайте (не Mini App).
    Верификация по SHA256(BOT_TOKEN), а не WebAppData.
    """
    widget_data: Dict[str, Any] = {
        "id": request.id,
        "first_name": request.first_name,
        "auth_date": request.auth_date,
        "hash": request.hash,
    }
    if request.last_name:
        widget_data["last_name"] = request.last_name
    if request.username:
        widget_data["username"] = request.username
    if request.photo_url:
        widget_data["photo_url"] = request.photo_url

    if not verify_telegram_widget_data(widget_data):
        raise HTTPException(status_code=401, detail="Invalid Telegram widget data")

    # Ищем по telegram_id, или по уже привязанному аккаунту
    result = await db.execute(select(User).where(User.telegram_id == request.id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=request.id,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.first_name = request.first_name
        user.last_name = request.last_name
        user.username = request.username
        await db.commit()

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    token = create_jwt_token(user_id=user.id, telegram_id=user.telegram_id)
    return _build_response(user, token)


# ---------------------------------------------------------------------------
# Регистрация по email
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя через email + пароль
    """
    # Проверяем уникальность email
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email уже используется")

    # Проверяем уникальность display_name
    result = await db.execute(select(User).where(User.display_name == request.display_name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")

    email_lower = request.email.lower()
    user = User(
        email=email_lower,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        is_admin=email_lower in settings.owner_emails,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_jwt_token(user_id=user.id)
    return _build_response(user, token)


# ---------------------------------------------------------------------------
# Вход по email / display_name
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Вход по email или display_name + пароль
    """
    login_value = request.login.strip()

    # Ищем по email
    result = await db.execute(select(User).where(User.email == login_value.lower()))
    user = result.scalar_one_or_none()

    # Если не нашли по email — ищем по display_name
    if not user:
        result = await db.execute(select(User).where(User.display_name == login_value))
        user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    # Автоматически ставим is_admin если email в OWNER_EMAILS
    if user.email and user.email.lower() in settings.owner_emails and not user.is_admin:
        user.is_admin = True
        await db.commit()

    token = create_jwt_token(user_id=user.id, telegram_id=user.telegram_id)
    return _build_response(user, token)
