"""
Telegram Bot на aiogram 3.x
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import settings

# Импорт хендлеров
from apps.bot.handlers import start, admin, channel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота"""
    # Инициализация бота
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)

    # Получаем информацию о боте и сохраняем username в настройки
    try:
        bot_info = await bot.get_me()
        if bot_info.username:
            settings.BOT_USERNAME = bot_info.username
            logger.info(f"✅ Bot username: @{bot_info.username}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить username бота: {e}")
        # Используем значение из env или дефолтное
        if not hasattr(settings, 'BOT_USERNAME') or not settings.BOT_USERNAME:
            settings.BOT_USERNAME = "noonyashop_bot"

    # Инициализация диспетчера с FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    logger.info("📝 Регистрация роутеров...")
    dp.include_router(start.router)
    logger.info("✅ Роутер start зарегистрирован")
    dp.include_router(admin.router)
    logger.info("✅ Роутер admin зарегистрирован")
    dp.include_router(channel.router)
    logger.info("✅ Роутер channel зарегистрирован")

    logger.info("🤖 Bot starting...")
    logger.info(f"👤 Owner IDs: {settings.owner_ids}")

    try:
        # Удаляем webhook, если он активен (для работы в режиме polling)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален, переходим на polling")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить webhook (возможно, его нет): {e}")
        
        # Запуск polling с игнорированием старых обновлений
        # drop_pending_updates=True уже установлен в delete_webhook выше
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Дополнительно игнорируем старые обновления
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
