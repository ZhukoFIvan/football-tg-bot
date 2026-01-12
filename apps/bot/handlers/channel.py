"""
Обработчик автоматических комментариев в группе обсуждений канала
"""
import logging
import re
import json
import asyncio
import aiohttp
from aiogram import Router, Bot
from aiogram.types import Message
from sqlalchemy import select

from core.db.session import AsyncSessionLocal
from core.db.models import SiteSettings
from core.config import settings

router = Router()
logger = logging.getLogger(__name__)


@router.channel_post()
async def handle_channel_post(message: Message, bot: Bot):
    """
    Обработчик новых постов в канале
    Отправляет комментарий в группу обсуждений канала
    """
    try:
        # Проверяем, что это действительно пост в канале, а не сообщение в группе
        if message.chat.type != "channel":
            logger.debug(f"Пропускаем сообщение - это не канал: {message.chat.type}")
            return
        
        # Проверяем, что это не forwarded сообщение и не reply
        if message.forward_from_chat or message.reply_to_message:
            logger.debug(f"Пропускаем сообщение - это forwarded или reply")
            return
        
        logger.info(f"Получен пост в канале: {message.chat.id}, message_id: {message.message_id}, тип: {message.chat.type}")
        
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
            
            logger.info(f"Настроенный канал: {configured_channel_id}, текущий: {message.chat.id}")
            
            # Проверяем, что пост из настроенного канала
            current_channel_id = str(message.chat.id)
            
            if configured_channel_id != current_channel_id:
                logger.debug(f"Пост из другого канала: {current_channel_id} != {configured_channel_id}")
                return
            
            # Получаем информацию о канале и связанной группе обсуждений
            try:
                logger.info(f"Получаем информацию о канале {message.chat.id}")
                
                linked_chat_id = None
                
                # Пробуем получить linked_chat_id через get_chat
                try:
                    chat = await bot.get_chat(message.chat.id)
                    
                    # В aiogram 3.x linked_chat может быть в разных местах
                    if hasattr(chat, 'linked_chat') and chat.linked_chat:
                        linked_chat_id = chat.linked_chat.id
                        logger.info(f"Найден linked_chat через chat.linked_chat: {linked_chat_id}")
                    elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                        linked_chat_id = chat.linked_chat_id
                        logger.info(f"Найден linked_chat_id через chat.linked_chat_id: {linked_chat_id}")
                except Exception as chat_error:
                    # Если не получилось распарсить Chat из-за новых полей, используем прямой HTTP запрос к API
                    logger.warning(f"Ошибка при получении информации о канале через get_chat: {chat_error}")
                    
                    # Используем прямой HTTP запрос к Telegram API для получения linked_chat_id
                    try:
                        api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getChat"
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.post(api_url, json={"chat_id": message.chat.id}) as response:
                                data = await response.json()
                                if data.get("ok") and "result" in data:
                                    result = data["result"]
                                    if "linked_chat_id" in result:
                                        linked_chat_id = result["linked_chat_id"]
                                        logger.info(f"Найден linked_chat_id через прямой API запрос: {linked_chat_id}")
                    except Exception as api_error:
                        logger.error(f"Ошибка при получении linked_chat_id через прямой API: {api_error}")
                
                # Если linked_chat_id не найден, возможно канал не имеет связанной группы
                if not linked_chat_id:
                    logger.warning(f"Не удалось найти linked_chat_id для канала {message.chat.id}")
                    logger.warning("Убедитесь, что канал имеет связанную группу обсуждений")
                    return
                
                logger.info(f"Найдена группа обсуждений: {linked_chat_id}")
                logger.info(f"Текст комментария: {comment_text[:50]}...")
                logger.info(f"ID поста в канале: {message.message_id}")
                
                # Небольшая задержка, чтобы Telegram успел создать сообщение в группе обсуждений
                await asyncio.sleep(3)
                
                # Для комментариев к посту в канале нужно использовать формат:
                # chat_id = f"{linked_chat_id}_{message.message_id}"
                # Это специальный формат для комментариев к постам в каналах
                try:
                    logger.info(f"Отправляю комментарий в группу {linked_chat_id} для поста {message.message_id}")
                    
                    send_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
                    
                    # Пробуем использовать специальный формат chat_id для комментариев к постам
                    # Формат: chat_id = f"{group_id}_{channel_message_id}"
                    special_chat_id = f"{linked_chat_id}_{message.message_id}"
                    
                    payload = {
                        "chat_id": special_chat_id,
                        "text": comment_text,
                        "parse_mode": "HTML"
                    }
                    
                    async with aiohttp.ClientSession() as http_session:
                        async with http_session.post(send_url, json=payload) as response:
                            result = await response.json()
                            logger.info(f"Ответ API с специальным chat_id: {result}")
                            if result.get("ok"):
                                logger.info(f"✅ Комментарий успешно отправлен! Message ID: {result.get('result', {}).get('message_id')}")
                            else:
                                error_desc = result.get('description', 'Unknown error')
                                logger.warning(f"⚠️ Ошибка с специальным chat_id: {error_desc}")
                                
                                # Если не получилось, пробуем обычный способ с reply_to_message_id
                                logger.info("Пробую обычный способ с reply_to_message_id")
                                
                                payload_reply = {
                                    "chat_id": linked_chat_id,
                                    "text": comment_text,
                                    "reply_to_message_id": message.message_id,
                                    "parse_mode": "HTML"
                                }
                                
                                await asyncio.sleep(1)
                                async with http_session.post(send_url, json=payload_reply) as reply_response:
                                    reply_result = await reply_response.json()
                                    logger.info(f"Ответ API с reply_to_message_id: {reply_result}")
                                    if reply_result.get("ok"):
                                        logger.info(f"✅ Комментарий успешно отправлен с reply_to_message_id!")
                                    else:
                                        error_desc2 = reply_result.get('description', 'Unknown error')
                                        logger.error(f"❌ Ошибка с reply_to_message_id: {error_desc2}")
                                        raise Exception(f"Не удалось отправить комментарий: {error_desc2}")
                                
                except Exception as e:
                    logger.error(f"Ошибка при отправке комментария через прямой API: {e}", exc_info=True)
                    # Fallback: пробуем через aiogram
                    try:
                        logger.info("Пробую отправить комментарий через aiogram")
                        await bot.send_message(
                            chat_id=linked_chat_id,
                            text=comment_text,
                            reply_to_message_id=message.message_id,
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ Комментарий успешно отправлен через aiogram")
                    except Exception as e2:
                        logger.error(f"Ошибка при отправке комментария через aiogram: {e2}", exc_info=True)
                    
            except Exception as e:
                logger.error(f"Ошибка при получении информации о канале: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике постов канала: {e}")
