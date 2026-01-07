"""
Клавиатуры для Telegram бота
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    # Пустая клавиатура - пользователи будут использовать веб-приложение
    keyboard = ReplyKeyboardMarkup(
        keyboard=[],
        resize_keyboard=True
    )
    return keyboard


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast"),
            ],
        ]
    )
    return keyboard


def get_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены рассылки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel"),
            ]
        ]
    )
    return keyboard
