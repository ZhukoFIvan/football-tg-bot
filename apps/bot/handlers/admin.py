"""
Обработчики для администраторов
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from apps.bot.keyboards import get_admin_menu_keyboard
from core.config import settings

router = Router()


def is_admin(telegram_id: int) -> bool:
    """Проверка что пользователь - администратор"""
    return telegram_id in settings.owner_ids


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "👨‍💼 <b>Админ-панель</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_menu_keyboard()
    )


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # TODO: Получить статистику из API
    stats_text = """
📊 <b>Статистика</b>

👥 <b>Пользователи:</b>
• Всего: 1523
• Новых сегодня: 12
• С заказами: 342

📦 <b>Заказы:</b>
• Всего: 1856
• Ожидают оплаты: 23
• Оплачено: 1542

💰 <b>Выручка:</b>
• Всего: 2,345,678 ₽
• За сегодня: 12,345 ₽
• Средний чек: 1,263 ₽

🎮 <b>Товары:</b>
• Всего: 234
• Активных: 198
• Нет в наличии: 12
"""

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_orders")
async def callback_admin_orders(callback: CallbackQuery):
    """Показать последние заказы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # TODO: Получить заказы из API
    await callback.message.edit_text(
        "📦 <b>Последние заказы</b>\n\n"
        "Заказ #1856 - 1999 ₽ - ⏳ Ожидает\n"
        "Заказ #1855 - 2499 ₽ - ✅ Оплачен\n"
        "Заказ #1854 - 899 ₽ - ✅ Завершен\n\n"
        "<i>Полный список доступен в веб-панели</i>",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    """Показать информацию о пользователях"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # TODO: Получить пользователей из API
    await callback.message.edit_text(
        "👥 <b>Пользователи</b>\n\n"
        "Всего: 1523\n"
        "Новых сегодня: 12\n"
        "Забанено: 5\n\n"
        "<i>Управление пользователями доступно в веб-панели</i>",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products")
async def callback_admin_products(callback: CallbackQuery):
    """Показать информацию о товарах"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # TODO: Получить товары из API
    await callback.message.edit_text(
        "🎮 <b>Товары</b>\n\n"
        "Всего: 234\n"
        "Активных: 198\n"
        "Нет в наличии: 12\n\n"
        "<i>Управление товарами доступно в веб-панели</i>",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
