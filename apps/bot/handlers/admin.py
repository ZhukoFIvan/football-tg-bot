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
from sqlalchemy import select, insert, update

from apps.bot.keyboards import get_admin_menu_keyboard, get_broadcast_cancel_keyboard, get_channel_text_cancel_keyboard
from core.config import settings
from core.db.session import AsyncSessionLocal
from core.db.models import User, SiteSettings

router = Router()
logger = logging.getLogger(__name__)


class BroadcastStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_text = State()
    waiting_for_button_text = State()


class ChannelTextStates(StatesGroup):
    """Состояния для установки текста канала"""
    waiting_for_channel_id = State()
    waiting_for_comment_text = State()


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
                    web_app=WebAppInfo(url="https://romixstore.ru")
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


# ==================== УСТАНОВКА ТЕКСТА ДЛЯ КАНАЛА ====================

@router.callback_query(F.data == "admin_channel_text")
async def callback_channel_text_start(callback: CallbackQuery, state: FSMContext):
    """Начать процесс установки текста для канала"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # Получаем текущие настройки
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_id")
            )
            channel_setting = result.scalar_one_or_none()
            
            result_text = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_comment_text")
            )
            text_setting = result_text.scalar_one_or_none()
            
            current_channel = channel_setting.value if channel_setting else "не установлен"
            current_text = text_setting.value if text_setting else "не установлен"
            
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            current_channel = "ошибка загрузки"
            current_text = "ошибка загрузки"

    await callback.message.edit_text(
        "💬 <b>Установка текста для канала</b>\n\n"
        f"<b>Текущие настройки:</b>\n"
        f"📢 ID/Username канала: <code>{current_channel}</code>\n"
        f"💬 Текст комментария: <code>{current_text}</code>\n\n"
        "Отправьте ID или @username канала, в котором бот будет оставлять комментарии.\n\n"
        "<i>Например: @your_channel или -1001234567890</i>\n\n"
        "<b>⚠️ Важно:</b> Бот должен быть администратором канала с правом комментирования!",
        reply_markup=get_channel_text_cancel_keyboard()
    )
    await state.set_state(ChannelTextStates.waiting_for_channel_id)
    await callback.answer()


@router.callback_query(F.data == "channel_text_cancel")
async def callback_channel_text_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменить установку текста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "❌ Установка текста отменена.",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.message(ChannelTextStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext, bot: Bot):
    """Обработка ID/username канала"""
    logger.info(f"Получено сообщение в состоянии waiting_for_channel_id: {message.text}")
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    channel_id = message.text.strip() if message.text else ""
    if not channel_id:
        await message.answer(
            "❌ ID/username канала не может быть пустым.\n\n"
            "Отправьте ID или @username канала.",
            reply_markup=get_channel_text_cancel_keyboard()
        )
        return

    # Проверяем, что бот может отправлять сообщения в канал
    try:
        chat = await bot.get_chat(channel_id)
        # Проверяем права бота
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        
        if not bot_member.can_post_messages:
            await message.answer(
                f"❌ Бот не имеет прав на отправку сообщений в канале {chat.title}.\n\n"
                "Сделайте бота администратором с правом комментирования!",
                reply_markup=get_channel_text_cancel_keyboard()
            )
            return
            
        await state.update_data(channel_id=str(chat.id))
        
        await message.answer(
            f"✅ Канал найден: <b>{chat.title}</b>\n\n"
            "Теперь отправьте текст, который бот будет оставлять в комментариях к каждому новому посту.\n\n"
            "<i>Вы можете использовать HTML разметку для форматирования текста.</i>",
            reply_markup=get_channel_text_cancel_keyboard()
        )
        await state.set_state(ChannelTextStates.waiting_for_comment_text)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке канала: {e}", exc_info=True)
        error_msg = str(e).replace("<", "&lt;").replace(">", "&gt;")
        await message.answer(
            f"❌ Не удалось найти канал или бот не имеет доступа.\n\n"
            f"Ошибка: <code>{error_msg}</code>\n\n"
            "Убедитесь, что:\n"
            "1. ID/username указан правильно\n"
            "2. Бот добавлен в канал как администратор\n"
            "3. У бота есть право комментирования",
            reply_markup=get_channel_text_cancel_keyboard(),
            parse_mode="HTML"
        )


@router.message(ChannelTextStates.waiting_for_comment_text)
async def process_comment_text(message: Message, state: FSMContext):
    """Обработка текста комментария"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    comment_text = message.text or message.caption or ""
    if not comment_text.strip():
        await message.answer(
            "❌ Текст комментария не может быть пустым.\n\n"
            "Отправьте текст комментария.",
            reply_markup=get_channel_text_cancel_keyboard()
        )
        return

    data = await state.get_data()
    channel_id = data.get("channel_id", "")

    # Сохраняем настройки в БД
    async with AsyncSessionLocal() as session:
        try:
            # Сохраняем ID канала
            result = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_id")
            )
            channel_setting = result.scalar_one_or_none()
            
            if channel_setting:
                channel_setting.value = channel_id
            else:
                channel_setting = SiteSettings(
                    key="channel_id",
                    value=channel_id,
                    description="ID канала для автокомментариев"
                )
                session.add(channel_setting)
            
            # Сохраняем текст комментария
            result_text = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_comment_text")
            )
            text_setting = result_text.scalar_one_or_none()
            
            if text_setting:
                text_setting.value = comment_text
            else:
                text_setting = SiteSettings(
                    key="channel_comment_text",
                    value=comment_text,
                    description="Текст для автокомментариев в канале"
                )
                session.add(text_setting)
            
            await session.commit()
            
            await message.answer(
                "✅ <b>Настройки сохранены!</b>\n\n"
                f"📢 <b>Канал:</b> <code>{channel_id}</code>\n"
                f"💬 <b>Текст комментария:</b>\n{comment_text}\n\n"
                "Теперь бот будет автоматически комментировать каждый новый пост в этом канале.",
                reply_markup=get_admin_menu_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
            await message.answer(
                f"❌ Произошла ошибка при сохранении: {str(e)}",
                reply_markup=get_admin_menu_keyboard()
            )
        finally:
            await state.clear()
