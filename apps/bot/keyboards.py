"""
Клавиатуры для Telegram бота
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from core.config import settings


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная inline-клавиатура с кнопкой магазина"""
    # Используем FRONTEND_URL из настроек
    web_app_url = settings.FRONTEND_URL if settings.FRONTEND_URL else "https://noonyashop.ru"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Открыть магазин",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ]
        ]
    )
    return keyboard


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="💬 Установить текст для канала", callback_data="admin_channel_text"),
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
