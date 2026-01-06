"""
Обработчики для администраторов
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.keyboards import get_admin_menu_keyboard, get_broadcast_cancel_keyboard
from core.config import settings
from core.db.session import AsyncSessionLocal
from core.db.models import User, Payment
from sqlalchemy import func, and_
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)


class BroadcastStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_text = State()
    waiting_for_button_text = State()


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


@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начать процесс рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>Создание рассылки</b>\n\n"
        "Отправьте текст рассылки, который будет отправлен всем пользователям бота.\n\n"
        "<i>Вы можете использовать HTML разметку для форматирования текста.</i>",
        reply_markup=get_broadcast_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()


@router.callback_query(F.data == "broadcast_cancel")
async def callback_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменить рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """Обработка текста рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    text = message.text or message.caption or ""
    if not text.strip():
        await message.answer(
            "❌ Текст рассылки не может быть пустым.\n\n"
            "Отправьте текст рассылки или отмените операцию.",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return

    await state.update_data(broadcast_text=text)
    await message.answer(
        "✅ Текст рассылки сохранен.\n\n"
        "Теперь отправьте название кнопки, которая будет внизу сообщения.\n"
        "Эта кнопка будет вести на /start в этом боте.\n\n"
        "<i>Например: \"Перейти в магазин\" или \"Открыть бота\"</i>",
        reply_markup=get_broadcast_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_button_text)


@router.message(BroadcastStates.waiting_for_button_text)
async def process_broadcast_button_text(message: Message, state: FSMContext, bot: Bot):
    """Обработка названия кнопки и отправка рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    button_text = message.text or message.caption or ""
    if not button_text.strip():
        await message.answer(
            "❌ Название кнопки не может быть пустым.\n\n"
            "Отправьте название кнопки или отмените операцию.",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")

    # Получаем информацию о боте для создания ссылки
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    # Создаем клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    url=f"https://t.me/{bot_username}?start=1"
                )
            ]
        ]
    )

    # Получаем всех пользователей из БД
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.is_banned == False)
            )
            users = result.scalars().all()
            total_users = len(users)

            if total_users == 0:
                await message.answer(
                    "❌ В базе данных нет пользователей для рассылки.",
                    reply_markup=get_admin_menu_keyboard()
                )
                await state.clear()
                return

            # Отправляем рассылку
            sent_count = 0
            failed_count = 0

            await message.answer(
                f"📤 Начинаю рассылку для {total_users} пользователей...\n\n"
                "<i>Это может занять некоторое время.</i>"
            )

            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=broadcast_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                    # Небольшая задержка, чтобы не превысить лимиты Telegram API
                    await asyncio.sleep(0.05)  # 50ms между сообщениями
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения пользователю {user.telegram_id}: {e}")
                    failed_count += 1
                    # Задержка даже при ошибке, чтобы не спамить API
                    await asyncio.sleep(0.05)

            await message.answer(
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• Всего пользователей: {total_users}\n"
                f"• Успешно отправлено: {sent_count}\n"
                f"• Ошибок: {failed_count}",
                reply_markup=get_admin_menu_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            await message.answer(
                f"❌ Произошла ошибка при выполнении рассылки: {str(e)}",
                reply_markup=get_admin_menu_keyboard()
            )
        finally:
            await state.clear()


@router.callback_query(F.data == "admin_payments")
async def callback_admin_payments(callback: CallbackQuery):
    """Показать статистику платежей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    try:
        # Получить статистику платежей из БД
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            month_start = now - timedelta(days=30)

            # Всего платежей
            total_payments = await session.scalar(select(func.count(Payment.id))) or 0

            # По статусам
            pending = await session.scalar(
                select(func.count(Payment.id)).where(Payment.status == "pending")
            ) or 0
            success = await session.scalar(
                select(func.count(Payment.id)).where(Payment.status == "success")
            ) or 0
            failed = await session.scalar(
                select(func.count(Payment.id)).where(Payment.status == "failed")
            ) or 0
            cancelled = await session.scalar(
                select(func.count(Payment.id)).where(Payment.status == "cancelled")
            ) or 0
            refunded = await session.scalar(
                select(func.count(Payment.id)).where(Payment.status == "refunded")
            ) or 0

            # Суммы
            success_amount = await session.scalar(
                select(func.sum(Payment.amount)).where(Payment.status == "success")
            ) or 0.0
            failed_amount = await session.scalar(
                select(func.sum(Payment.amount)).where(Payment.status == "failed")
            ) or 0.0
            cancelled_amount = await session.scalar(
                select(func.sum(Payment.amount)).where(Payment.status == "cancelled")
            ) or 0.0

            # По периодам
            payments_today = await session.scalar(
                select(func.count(Payment.id)).where(Payment.created_at >= today_start)
            ) or 0
            payments_this_week = await session.scalar(
                select(func.count(Payment.id)).where(Payment.created_at >= week_start)
            ) or 0
            payments_this_month = await session.scalar(
                select(func.count(Payment.id)).where(Payment.created_at >= month_start)
            ) or 0

            # Выручка по периодам
            revenue_today = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(Payment.status == "success", Payment.created_at >= today_start)
                )
            ) or 0.0
            revenue_this_week = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(Payment.status == "success", Payment.created_at >= week_start)
                )
            ) or 0.0
            revenue_this_month = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(Payment.status == "success", Payment.created_at >= month_start)
                )
            ) or 0.0

            # По провайдерам
            freekassa_count = await session.scalar(
                select(func.count(Payment.id)).where(Payment.provider == "freekassa")
            ) or 0
            paypalych_count = await session.scalar(
                select(func.count(Payment.id)).where(Payment.provider == "paypalych")
            ) or 0

            # По методам
            card_count = await session.scalar(
                select(func.count(Payment.id)).where(Payment.payment_method == "card")
            ) or 0
            sbp_count = await session.scalar(
                select(func.count(Payment.id)).where(Payment.payment_method == "sbp")
            ) or 0

            stats_text = f"""
💳 <b>Статистика платежей</b>

📊 <b>Общая статистика:</b>
• Всего платежей: {total_payments}
• Сегодня: {payments_today}
• За неделю: {payments_this_week}
• За месяц: {payments_this_month}

✅ <b>Успешные:</b>
• Количество: {success}
• Сумма: {float(success_amount):,.2f} ₽

⏳ <b>Ожидают оплаты:</b>
• Количество: {pending}

❌ <b>Отменено:</b>
• Количество: {cancelled}
• Сумма: {float(cancelled_amount):,.2f} ₽

⚠️ <b>Ошибки:</b>
• Количество: {failed}
• Сумма: {float(failed_amount):,.2f} ₽

🔄 <b>Возвраты:</b>
• Количество: {refunded}

💰 <b>Выручка:</b>
• Сегодня: {float(revenue_today):,.2f} ₽
• За неделю: {float(revenue_this_week):,.2f} ₽
• За месяц: {float(revenue_this_month):,.2f} ₽

🏦 <b>По провайдерам:</b>
• FreeKassa: {freekassa_count}
• PayPaly: {paypalych_count}

💳 <b>По методам оплаты:</b>
• Карта: {card_count}
• СБП: {sbp_count}
"""

            await callback.message.edit_text(
                stats_text,
                reply_markup=get_admin_menu_keyboard()
            )
            await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении статистики платежей: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при получении статистики платежей: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
