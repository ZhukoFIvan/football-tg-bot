"""
Обработчик команды /start
"""
import logging
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, URLInputFile, ReplyKeyboardRemove
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.session import AsyncSessionLocal
from core.db.models import User

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """
    Обработчик команды /start
    """
    # Регистрируем или обновляем пользователя в БД
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Создаем нового пользователя
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name or "",
                    last_name=message.from_user.last_name or "",
                    is_admin=message.from_user.id in settings.owner_ids
                )
                session.add(user)
            else:
                # Обновляем данные существующего пользователя
                user.username = message.from_user.username
                user.first_name = message.from_user.first_name or ""
                user.last_name = message.from_user.last_name or ""
                user.is_admin = message.from_user.id in settings.owner_ids
            
            await session.commit()
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            await session.rollback()
    
    # Определяем бренд и соответствующий текст/фото
    brand = settings.BRAND.lower() if hasattr(settings, 'BRAND') else "noonyashop"
    
    if brand == "romixstore":
        welcome_text = """<b>Что умеет бот?</b>

💎 В магазине ROMIX STORE ты сможешь задонатить быстро, а главное безопасно в FC MOBILE!

Связь с поддержкой
@romixstore_support"""
        photo_path = "uploads/welcomeRoma.JPG"
    else:  # noonyashop (по умолчанию)
        welcome_text = """<b>Что умеет бот?</b>

💎 В магазине NOONYA SHOP ты сможешь задонатить быстро, а главное безопасно в FC MOBILE!

Связь с поддержкой
@noonyashop_support"""
        photo_path = "uploads/welcome.jpg"
    
    # Удаляем главную клавиатуру (если она была)
    remove_keyboard = ReplyKeyboardRemove(remove_keyboard=True)
    
    # Сначала пробуем локальный файл
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=remove_keyboard,
            parse_mode="HTML"
        )
    # Если локального файла нет, пробуем загрузить с сервера
    elif settings.API_PUBLIC_URL:
        try:
            photo_url = f"{settings.API_PUBLIC_URL}/{photo_path}"
            photo = URLInputFile(photo_url)
            await message.answer_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=remove_keyboard,
                parse_mode="HTML"
            )
        except:
            # Если не получилось загрузить фото, отправляем просто текст
            await message.answer(
                welcome_text,
                reply_markup=remove_keyboard,
                parse_mode="HTML"
            )
    else:
        # Если фото нет, отправляем просто текст
        await message.answer(
            welcome_text,
            reply_markup=remove_keyboard,
            parse_mode="HTML"
        )
