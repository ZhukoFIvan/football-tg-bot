"""
Клавиатуры для Telegram бота
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Привет"),
                KeyboardButton(text="Как дела?"),
            ]
        ],
        resize_keyboard=True
    )
    return keyboard
