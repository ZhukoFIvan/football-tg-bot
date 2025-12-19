"""
Обработчик команды /start
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

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

🎮 Здесь вы сможете приобрести ключи для популярных игр.

<i>WebApp кнопки и каталог будут добавлены в ближайшее время.</i>
"""

    await message.answer(welcome_text)
