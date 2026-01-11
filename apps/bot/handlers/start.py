"""
Обработчик команды /start
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, URLInputFile, ReplyKeyboardRemove
import os

from core.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    """
    welcome_text = """<b>Что умеет бот?</b>

💎 В магазине NOONYA SHOP ты сможешь задонатить быстро, а главное безопасно в FC MOBILE!

Связь с поддержкой
@noonyashop_support"""

    # Путь к изображению приветствия
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
            photo_url = f"{settings.API_PUBLIC_URL}/uploads/welcome.jpg"
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
