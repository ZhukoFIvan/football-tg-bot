"""
Обработчик автоматических комментариев в группе обсуждений канала
"""
import logging
from aiogram import Router, Bot
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
    Отправляет комментарий в группу обсуждений канала
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
            
            # Получаем информацию о канале и связанной группе обсуждений
            try:
                chat = await bot.get_chat(message.chat.id)
                
                # Проверяем, есть ли связанная группа обсуждений
                # В aiogram 3.x linked_chat может быть доступен через chat.linked_chat или через get_chat
                linked_chat_id = None
                
                # Пробуем получить linked_chat_id разными способами
                if hasattr(chat, 'linked_chat') and chat.linked_chat:
                    linked_chat_id = chat.linked_chat.id
                elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                    linked_chat_id = chat.linked_chat_id
                else:
                    # Пробуем получить через API напрямую
                    try:
                        full_chat = await bot.get_chat(message.chat.id)
                        if hasattr(full_chat, 'linked_chat_id'):
                            linked_chat_id = full_chat.linked_chat_id
                    except:
                        pass
                
                if linked_chat_id:
                    logger.info(f"Найдена группа обсуждений: {linked_chat_id}")
                    
                    # Отправляем комментарий в группу обсуждений
                    # В группах обсуждений сообщения отображаются как комментарии к постам
                    try:
                        await bot.send_message(
                            chat_id=linked_chat_id,
                            text=comment_text,
                            parse_mode="HTML"
                        )
                        logger.info(f"Комментарий успешно отправлен в группу обсуждений {linked_chat_id} для поста {message.message_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке комментария в группу обсуждений: {e}")
                else:
                    logger.warning(f"У канала {message.chat.id} нет связанной группы обсуждений")
                    
            except Exception as e:
                logger.error(f"Ошибка при получении информации о канале: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике постов канала: {e}")
