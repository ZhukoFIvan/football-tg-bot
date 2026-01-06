"""
Клавиатуры для Telegram бота
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


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


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders"),
            ],
            [
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
                InlineKeyboardButton(text="🎮 Товары", callback_data="admin_products"),
            ],
            [
                InlineKeyboardButton(text="💳 Статистика платежей", callback_data="admin_payments"),
            ],
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
