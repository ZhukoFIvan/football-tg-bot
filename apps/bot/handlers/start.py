"""
Обработчик команды /start
"""
import logging
import os
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, URLInputFile
from sqlalchemy import select

from core.config import settings
from core.db.session import AsyncSessionLocal
from core.db.models import User
from apps.bot.keyboards import get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Обработчик команды /start"""
    logger.info(f"🔵 /start от {message.from_user.id}")
    
    try:
        # Регистрируем или обновляем пользователя в БД
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    user = User(
                        telegram_id=message.from_user.id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name or "",
                        last_name=message.from_user.last_name or "",
                        is_admin=message.from_user.id in settings.owner_ids
                    )
                    session.add(user)
                    await session.commit()
                    logger.info(f"✅ Пользователь {message.from_user.id} создан")
                else:
                    user.username = message.from_user.username
                    user.first_name = message.from_user.first_name or ""
                    user.last_name = message.from_user.last_name or ""
                    user.is_admin = message.from_user.id in settings.owner_ids
                    await session.commit()
                    logger.info(f"✅ Пользователь {message.from_user.id} обновлен")
            except Exception as e:
                logger.error(f"Ошибка БД: {e}", exc_info=True)
                await session.rollback()
        
        # Определяем бренд
        brand = str(getattr(settings, 'BRAND', 'noonyashop')).lower().strip()
        
        if brand == "romixstore":
            welcome_text = """<b>Что умеет бот?</b>

💎 В магазине ROMIX STORE ты сможешь задонатить быстро, а главное безопасно в FC MOBILE!

Связь с поддержкой
@romixstore_support"""
            photo_path = "uploads/welcomeRoma.JPG"
        else:
            welcome_text = """<b>Что умеет бот?</b>

💎 В магазине NOONYA SHOP ты сможешь задонатить быстро, а главное безопасно в FC MOBILE!

Связь с поддержкой
@noonyashop_support"""
            photo_path = "uploads/welcome.jpg"
        
        shop_keyboard = get_main_keyboard()
        
        # Отправляем сообщение
        try:
            if os.path.exists(photo_path):
                photo = FSInputFile(photo_path)
                await message.answer_photo(
                    photo=photo,
                    caption=welcome_text,
                    reply_markup=shop_keyboard,
                    parse_mode="HTML"
                )
            elif settings.API_PUBLIC_URL:
                photo_url = f"{settings.API_PUBLIC_URL}/{photo_path}"
                photo = URLInputFile(photo_url)
                await message.answer_photo(
                    photo=photo,
                    caption=welcome_text,
                    reply_markup=shop_keyboard,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    welcome_text,
                    reply_markup=shop_keyboard,
                    parse_mode="HTML"
                )
            logger.info(f"✅ Сообщение отправлено {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}", exc_info=True)
            # Fallback - просто текст
            await message.answer(
                welcome_text,
                reply_markup=shop_keyboard,
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА /start: {e}", exc_info=True)
        try:
            await message.answer("❌ Ошибка. Попробуйте позже.")
        except:
            pass