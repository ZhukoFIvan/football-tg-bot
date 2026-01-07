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
from apps.bot.handlers import start, admin

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

    # Инициализация диспетчера с FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(admin.router)

    logger.info("🤖 Bot starting...")
    logger.info(f"👤 Owner IDs: {settings.owner_ids}")

    try:
        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
