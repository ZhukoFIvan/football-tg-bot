"""
Обработчик автоматических комментариев в группе обсуждений канала
"""
import logging
import re
import json
import asyncio
 import time
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

# Словарь для хранения активных задач обработки постов
# Ключ: channel_id, Значение: task
_active_tasks: dict[int, asyncio.Task] = {}

# Lock для синхронизации доступа к словарям
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
        
        # Сначала ждем 5 секунд, чтобы "собрать" все посты, которые могут прийти подряд
        # Это нужно, чтобы обработать только последний пост из серии
        logger.info("Ожидание 5 секунд для сбора всех постов...")
        for _ in range(10):  # 10 раз по 0.5 секунды = 5 секунд
            await asyncio.sleep(0.5)
            async with _post_lock:
                if channel_id in _last_post_ids:
                    last_message_id = _last_post_ids[channel_id]
                    # Если текущий пост НЕ является последним - отменяем обработку
                    if current_message_id != last_message_id:
                        logger.info(f"❌ Пост {current_message_id} НЕ является последним! Последний пост: {last_message_id}. Отменяю обработку.")
                        return
        
        # Дополнительная задержка, чтобы Telegram успел создать сообщение в группе обсуждений
        logger.info("Ожидание 3 секунд перед отправкой комментария...")
        for _ in range(6):  # 6 раз по 0.5 секунды = 3 секунды
            await asyncio.sleep(0.5)
            async with _post_lock:
                if channel_id in _last_post_ids:
                    last_message_id = _last_post_ids[channel_id]
                    # Если текущий пост НЕ является последним - отменяем обработку
                    if current_message_id != last_message_id:
                        logger.info(f"❌ Пост {current_message_id} НЕ является последним! Последний пост: {last_message_id}. Отменяю обработку.")
                        return
        
        # Проверяем еще раз перед отправкой (на случай, если за время задержки пришел новый пост)
        async with _post_lock:
            if channel_id in _last_post_ids:
                last_message_id = _last_post_ids[channel_id]
                # Если текущий пост НЕ является последним - отменяем обработку
                if current_message_id != last_message_id:
                    logger.info(f"❌ Пост {current_message_id} НЕ является последним перед отправкой! Последний пост: {last_message_id}. Отменяю обработку.")
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
                # Разбиваем задержку на части для проверки актуальности
                for _ in range(4):  # 4 раза по 0.5 секунды = 2 секунды
                    await asyncio.sleep(0.5)
                    async with _post_lock:
                        if channel_id in _last_post_ids:
                            last_message_id = _last_post_ids[channel_id]
                            # Если текущий пост НЕ является последним - отменяем обработку
                            if current_message_id != last_message_id:
                                logger.info(f"❌ Пост {current_message_id} НЕ является последним во время повтора! Последний пост: {last_message_id}. Отменяю обработку.")
                                return
                
                # Проверяем еще раз перед отправкой
                async with _post_lock:
                    if channel_id in _last_post_ids:
                        last_message_id = _last_post_ids[channel_id]
                        # Если текущий пост НЕ является последним - отменяем обработку
                        if current_message_id != last_message_id:
                            logger.info(f"❌ Пост {current_message_id} НЕ является последним перед повторной отправкой! Последний пост: {last_message_id}. Отменяю обработку.")
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
    finally:
        # Удаляем задачу из словаря после завершения, только если message_id все еще актуален
        async with _post_lock:
            if channel_id in _active_tasks and channel_id in _last_post_ids:
                # Удаляем задачу только если текущий message_id все еще последний
                # Это означает, что задача не была заменена новой
                if _last_post_ids[channel_id] == current_message_id:
                    stored_task = _active_tasks.get(channel_id)
                    if stored_task and (stored_task.done() or stored_task.cancelled()):
                        del _active_tasks[channel_id]
                        logger.debug(f"Задача для поста {current_message_id} удалена из словаря")


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
        
        # Проверяем, что пост свежий (не старше 30 секунд)
        # Это нужно, чтобы не обрабатывать старые посты, которые приходят с задержкой из-за polling
        current_time = time.time()
        if message.date:
            post_age = current_time - message.date.timestamp()
            if post_age > 30:
                logger.info(f"Пропускаем старый пост {current_message_id}, возраст: {post_age:.1f} секунд")
                return
        
        # Отменяем предыдущую задачу для этого канала, если она существует
        old_task = None
        old_message_id = None
        async with _post_lock:
            if channel_id in _active_tasks:
                old_task = _active_tasks[channel_id]
                task_status = "done" if old_task.done() else ("cancelled" if old_task.cancelled() else "running")
                logger.info(f"Найдена предыдущая задача для канала {channel_id}, статус: {task_status}")
                if not old_task.done() and not old_task.cancelled():
                    logger.info(f"⚠️ Отменяю обработку предыдущего поста, так как получен новый пост {current_message_id}")
                    old_task.cancel()
                else:
                    logger.info(f"Предыдущая задача уже завершена или отменена, пропускаем отмену")
                del _active_tasks[channel_id]
            
            # Обновляем последний message_id для этого канала
            if channel_id in _last_post_ids:
                old_message_id = _last_post_ids[channel_id]
                if old_message_id != current_message_id:
                    logger.info(f"Получен новый пост {current_message_id}, предыдущий был {old_message_id}. Обновляю.")
            else:
                logger.info(f"Первый пост для канала {channel_id}, message_id: {current_message_id}")
            _last_post_ids[channel_id] = current_message_id
        
        # Ждем отмены предыдущей задачи вне lock, чтобы не блокировать
        if old_task and not old_task.done():
            try:
                await asyncio.wait_for(old_task, timeout=0.1)
                logger.info(f"✅ Предыдущая задача успешно отменена")
            except asyncio.CancelledError:
                logger.info(f"✅ Предыдущая задача отменена (CancelledError)")
            except asyncio.TimeoutError:
                logger.debug(f"Таймаут при ожидании отмены задачи")
            except Exception as e:
                logger.debug(f"Ошибка при ожидании отмены задачи: {e}")
        
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
                # Сохраняем задачу в словаре
                async with _post_lock:
                    _active_tasks[channel_id] = task
                logger.info(f"Создана задача для обработки поста {current_message_id}")
                    
            except Exception as e:
                logger.error(f"Ошибка при получении информации о канале: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике постов канала: {e}")
