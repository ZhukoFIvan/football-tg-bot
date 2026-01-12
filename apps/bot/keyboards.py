"""
Клавиатуры для Telegram бота
"""
import logging
from typing import Optional
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from core.config import settings

logger = logging.getLogger(__name__)


def get_main_keyboard() -> Optional[InlineKeyboardMarkup]:
    """Главная inline-клавиатура с кнопкой магазина"""
    # Используем FRONTEND_URL из настроек
    web_app_url = settings.FRONTEND_URL.strip() if settings.FRONTEND_URL else "https://noonyashop.ru"
    
    # Проверяем, что URL валидный (должен начинаться с https://)
    if not web_app_url or not web_app_url.startswith("https://"):
        logger.warning(f"FRONTEND_URL невалидный или пустой: '{settings.FRONTEND_URL}', кнопка не будет создана")
        return None
    
    try:
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
        logger.debug(f"Создана клавиатура с WebApp URL: {web_app_url}")
        return keyboard
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры: {e}")
        return None


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


def get_channel_text_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены установки текста канала"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="channel_text_cancel"),
            ]
        ]
    )
    return keyboard
