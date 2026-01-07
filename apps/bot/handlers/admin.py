"""
Обработчики для администраторов
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from apps.bot.keyboards import get_admin_menu_keyboard, get_broadcast_cancel_keyboard
from core.config import settings
from core.db.session import AsyncSessionLocal
from core.db.models import User

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

    # Создаем клавиатуру с WebApp кнопкой
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    web_app=WebAppInfo(url="https://noonyashop.ru")
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
