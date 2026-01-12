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

# Словарь для хранения последнего message_id поста для каждого канала
# Ключ: channel_id, Значение: last_message_id
_last_post_ids: dict[int, int] = {}

# Lock для синхронизации доступа к словарю
_post_lock = asyncio.Lock()


async def _process_post_comment(message: Message, bot: Bot, comment_text: str, linked_chat_id: int):
    """
    Внутренняя функция для обработки комментария к посту
    """
    channel_id = message.chat.id
    current_message_id = message.message_id
    
    try:
        logger.info(f"Найдена группа обсуждений: {linked_chat_id}")
        logger.info(f"Текст комментария: {comment_text[:50]}...")
        logger.info(f"ID поста в канале: {current_message_id}")
        
        # Увеличиваем задержку, чтобы Telegram успел создать сообщение в группе обсуждений
        # и обработать пост в канале
        logger.info("Ожидание 3 секунд перед отправкой комментария...")
        await asyncio.sleep(3)
        
        # Проверяем, не устарел ли этот пост (не появился ли новый)
        async with _post_lock:
            if channel_id in _last_post_ids:
                last_message_id = _last_post_ids[channel_id]
                if last_message_id != current_message_id:
                    logger.info(f"Пост {current_message_id} устарел, появился новый пост {last_message_id}. Пропускаем.")
                    return
        
        # Проверяем еще раз перед отправкой (на случай, если за время задержки пришел новый пост)
        async with _post_lock:
            if channel_id in _last_post_ids:
                last_message_id = _last_post_ids[channel_id]
                if last_message_id != current_message_id:
                    logger.info(f"Пост {current_message_id} устарел перед отправкой, появился новый пост {last_message_id}. Пропускаем.")
                    return
        
        # Для комментариев к посту в канале нужно использовать reply_to_message_id
        # message_id поста в канале совпадает с message_id соответствующего сообщения в группе обсуждений
        # Это создаст комментарий под постом, а не просто сообщение в чате
        try:
            logger.info(f"Отправляю комментарий в группу {linked_chat_id} с reply_to_message_id={current_message_id}")
            
            # Используем reply_to_message_id для создания комментария под постом
            # Это правильный способ оставлять комментарии к постам в канале
            await bot.send_message(
                chat_id=linked_chat_id,  # ID группы обсуждений
                text=comment_text,
                reply_to_message_id=current_message_id,  # ID поста в канале (совпадает с ID сообщения в группе)
                parse_mode="HTML"
            )
            logger.info(f"✅ Комментарий успешно отправлен под постом в канале!")
                        
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Ошибка при отправке комментария через aiogram: {error_msg}")
            
            # Если ошибка, пробуем еще раз через 2 секунды (возможно, сообщение еще не создано в группе)
            if "message to reply not found" in error_msg.lower() or "bad request" in error_msg.lower():
                logger.info("Пробую еще раз через 2 секунды...")
                await asyncio.sleep(2)
                
                # Проверяем еще раз, не устарел ли пост
                async with _post_lock:
                    if channel_id in _last_post_ids:
                        last_message_id = _last_post_ids[channel_id]
                        if last_message_id != current_message_id:
                            logger.info(f"Пост {current_message_id} устарел во время повтора. Пропускаем.")
                            return
                
                try:
                    await bot.send_message(
                        chat_id=linked_chat_id,
                        text=comment_text,
                        reply_to_message_id=current_message_id,
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Комментарий успешно отправлен после повтора!")
                except Exception as retry_error:
                    logger.error(f"❌ Ошибка после повтора: {retry_error}")
                    
                    # Пробуем через прямой HTTP запрос к API
                    logger.info("Пробую через прямой HTTP запрос к API...")
                    try:
                        send_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
                        payload = {
                            "chat_id": linked_chat_id,
                            "text": comment_text,
                            "reply_to_message_id": current_message_id,
                            "parse_mode": "HTML"
                        }
                        
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.post(send_url, json=payload) as response:
                                result = await response.json()
                                logger.info(f"Ответ API: {result}")
                                if result.get("ok"):
                                    logger.info(f"✅ Комментарий успешно отправлен через HTTP API!")
                                else:
                                    api_error = result.get('description', 'Unknown error')
                                    logger.error(f"❌ Ошибка через HTTP API: {api_error}")
                                    raise Exception(f"Не удалось отправить комментарий к посту: {api_error}")
                    except Exception as http_error:
                        logger.error(f"❌ Ошибка через HTTP API: {http_error}")
                        raise Exception(f"Не удалось отправить комментарий к посту: {http_error}")
            else:
                raise
    except asyncio.CancelledError:
        logger.info(f"Обработка поста {current_message_id} была отменена")
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке поста {current_message_id}: {e}", exc_info=True)


@router.channel_post()
async def handle_channel_post(message: Message, bot: Bot):
    """
    Обработчик новых постов в канале
    Отправляет комментарий в группу обсуждений канала
    Обрабатывает только последний пост, отменяя обработку предыдущих
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
        
        channel_id = message.chat.id
        current_message_id = message.message_id
        
        # Обновляем последний message_id для этого канала
        async with _post_lock:
            if channel_id in _last_post_ids:
                old_message_id = _last_post_ids[channel_id]
                if old_message_id != current_message_id:
                    logger.info(f"Получен новый пост {current_message_id}, предыдущий был {old_message_id}. Обновляю.")
            _last_post_ids[channel_id] = current_message_id
        
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
                
                # Создаем задачу для обработки этого поста
                # Задача будет проверять актуальность поста перед отправкой комментария
                task = asyncio.create_task(
                    _process_post_comment(message, bot, comment_text, linked_chat_id)
                )
                logger.info(f"Создана задача для обработки поста {current_message_id}")
                    
            except Exception as e:
                logger.error(f"Ошибка при получении информации о канале: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике постов канала: {e}")
