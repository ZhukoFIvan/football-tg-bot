"""
Клавиатуры для Telegram бота
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from core.config import settings


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    buttons = []
    
    # Добавляем кнопку веб-приложения, если настроен FRONTEND_URL
    if settings.FRONTEND_URL:
        buttons.append([
            KeyboardButton(
                text="🛒 Открыть магазин",
                web_app=WebAppInfo(url=settings.FRONTEND_URL)
            )
        ])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
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
