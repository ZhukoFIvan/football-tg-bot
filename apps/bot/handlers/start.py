"""
Обработчик команды /start
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from apps.bot.keyboards import get_main_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    """
    user = message.from_user

    welcome_text = f"""
👋 <b>Привет, {user.first_name}!</b>

Добро пожаловать в магазин игровых ключей!

🎮 Здесь вы можете приобрести ключи для популярных игр.
"""

    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
