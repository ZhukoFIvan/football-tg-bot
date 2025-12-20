"""
Обработчик команды /start
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from apps.bot.keyboards import get_main_menu_keyboard, get_webapp_keyboard

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

🎮 Здесь вы можете приобрести ключи для популярных игр:
• Steam, Epic Games, Origin
• PlayStation, Xbox, Nintendo
• Подарочные карты

💳 <b>Способы оплаты:</b>
• ⭐️ Telegram Stars
• 💳 Банковская карта

🚀 <b>Быстрая доставка:</b>
Ключи приходят автоматически сразу после оплаты!
"""

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard()
    )

    # Дополнительно отправить кнопку WebApp
    await message.answer(
        "🛍 Откройте каталог магазина:",
        reply_markup=get_webapp_keyboard()
    )
