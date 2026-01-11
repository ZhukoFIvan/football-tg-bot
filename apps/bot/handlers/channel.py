"""
Обработчик автоматических комментариев в канале
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message
from sqlalchemy import select

from core.db.session import AsyncSessionLocal
from core.db.models import SiteSettings

router = Router()
logger = logging.getLogger(__name__)


@router.channel_post()
async def handle_channel_post(message: Message, bot: Bot):
    """
    Обработчик новых постов в канале
    Автоматически добавляет комментарий под каждым постом
    """
    try:
        # Получаем настройки из БД
        async with AsyncSessionLocal() as session:
            # Получаем ID канала
            result_channel = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_id")
            )
            channel_setting = result_channel.scalar_one_or_none()
            
            # Получаем текст комментария
            result_text = await session.execute(
                select(SiteSettings).where(SiteSettings.key == "channel_comment_text")
            )
            text_setting = result_text.scalar_one_or_none()
            
            if not channel_setting or not text_setting:
                logger.info("Настройки автокомментирования не установлены")
                return
            
            configured_channel_id = str(channel_setting.value)
            comment_text = text_setting.value
            
            # Проверяем, что пост из настроенного канала
            current_channel_id = str(message.chat.id)
            
            if configured_channel_id != current_channel_id:
                logger.debug(f"Пост из другого канала: {current_channel_id} != {configured_channel_id}")
                return
            
            # Пытаемся отправить комментарий
            try:
                # Отправляем комментарий к посту
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=comment_text,
                    reply_to_message_id=message.message_id,
                    parse_mode="HTML"
                )
                logger.info(f"Комментарий успешно отправлен к посту {message.message_id} в канале {message.chat.id}")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке комментария: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике постов канала: {e}")
