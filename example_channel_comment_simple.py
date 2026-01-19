"""
ПРОСТОЙ ПРИМЕР: Отправка первого сообщения под новым постом в канале
Использует aiogram 3.x (как в вашем проекте)

ВАЖНО: В вашем проекте уже есть более продвинутая версия в apps/bot/handlers/channel.py
Этот файл - только для примера и обучения.
"""
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import ChatTypeFilter
from aiogram.enums import ChatType

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Вставьте ваш токен API бота
TOKEN = 'YOUR_BOT_TOKEN'


@router.channel_post(ChatTypeFilter(ChatType.CHANNEL))
async def handle_new_post(message: Message, bot: Bot):
    """
    Обработчик новых постов в канале
    
    ВАЖНО: Бот должен быть администратором канала с правами на отправку сообщений
    """
    try:
        # Проверяем, что это действительно пост в канале
        if message.chat.type != "channel":
            return
        
        logger.info(f"Получен новый пост в канале: {message.chat.id}, message_id: {message.message_id}")
        
        # Получаем информацию о канале и связанной группе обсуждений
        try:
            chat = await bot.get_chat(message.chat.id)
            
            # Получаем ID связанной группы обсуждений
            linked_chat_id = None
            if hasattr(chat, 'linked_chat') and chat.linked_chat:
                linked_chat_id = chat.linked_chat.id
            elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                linked_chat_id = chat.linked_chat_id
            
            if not linked_chat_id:
                logger.warning("Канал не имеет связанной группы обсуждений!")
                return
            
            logger.info(f"Найдена группа обсуждений: {linked_chat_id}")
            
            # Отправляем первое сообщение под постом
            # message_id поста в канале совпадает с message_id сообщения в группе обсуждений
            await bot.send_message(
                chat_id=linked_chat_id,  # ID группы обсуждений
                text="Первое сообщение под этим постом!",
                reply_to_message_id=message.message_id,  # ID поста (создает комментарий под постом)
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Сообщение успешно отправлено под постом!")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике: {e}", exc_info=True)


async def main():
    """Запуск бота"""
    # Создание бота и диспетчера
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    
    # Регистрация роутера
    dp.include_router(router)
    
    # Запуск polling
    logger.info("🤖 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
