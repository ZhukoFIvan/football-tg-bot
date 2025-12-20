"""
Обработчики заказов в боте
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from apps.bot.keyboards import get_order_keyboard, get_payment_method_keyboard

router = Router()


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    # TODO: Получить заказы из API
    await callback.message.edit_text(
        "📦 <b>Ваши заказы</b>\n\n"
        "У вас пока нет заказов.\n"
        "Оформите первый заказ в магазине! 🛍"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_details:"))
async def callback_order_details(callback: CallbackQuery):
    """Показать детали заказа"""
    order_id = int(callback.data.split(":")[1])

    # TODO: Получить заказ из API
    order_text = f"""
📦 <b>Заказ #{order_id}</b>

<b>Товары:</b>
• Cyberpunk 2077 x1 - 1999 ₽

<b>Итого:</b> 1999 ₽
<b>Статус:</b> ⏳ Ожидает оплаты

Выберите действие:
"""

    await callback.message.edit_text(
        order_text,
        reply_markup=get_order_keyboard(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_order:"))
async def callback_pay_order(callback: CallbackQuery):
    """Выбрать способ оплаты"""
    order_id = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        "💳 <b>Выберите способ оплаты:</b>\n\n"
        "⭐️ <b>Telegram Stars</b> - оплата через Telegram\n"
        "💳 <b>Банковская карта</b> - оплата через ЮKassa",
        reply_markup=get_payment_method_keyboard(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars:"))
async def callback_pay_stars(callback: CallbackQuery):
    """Оплата через Telegram Stars"""
    order_id = int(callback.data.split(":")[1])

    # TODO: Реализовать оплату через Telegram Stars
    await callback.answer(
        "⭐️ Оплата через Telegram Stars будет добавлена в ближайшее время!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("pay_card:"))
async def callback_pay_card(callback: CallbackQuery):
    """Оплата через банковскую карту"""
    order_id = int(callback.data.split(":")[1])

    # TODO: Реализовать оплату через ЮKassa
    await callback.answer(
        "💳 Оплата через ЮKassa будет добавлена в ближайшее время!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("cancel_order:"))
async def callback_cancel_order(callback: CallbackQuery):
    """Отменить заказ"""
    order_id = int(callback.data.split(":")[1])

    # TODO: Отменить заказ через API
    await callback.message.edit_text(
        f"❌ Заказ #{order_id} отменен.\n\n"
        "Товары возвращены на склад."
    )
    await callback.answer("Заказ отменен")
