"""
Фоновые задачи (cron-like) для автоматической очистки
"""
import asyncio
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.db.session import AsyncSessionLocal
from core.db.models import Section
from core.storage import delete_file

logger = logging.getLogger(__name__)


async def cleanup_expired_sections():
    """
    Удаляет секции, у которых истекло время (end_time < now)
    Также удаляет связанные изображения
    """
    async with AsyncSessionLocal() as db:
        try:
            # Найти все секции с истекшим временем
            result = await db.execute(
                select(Section).where(
                    Section.end_time.isnot(None),
                    Section.end_time < datetime.utcnow()
                )
            )
            expired_sections = result.scalars().all()

            if not expired_sections:
                logger.info("No expired sections found")
                return

            logger.info(
                f"Found {len(expired_sections)} expired sections to delete")

            for section in expired_sections:
                # Удалить изображение секции
                if section.image:
                    delete_file(section.image)
                    logger.info(
                        f"Deleted image for section {section.id}: {section.image}")

                # Удалить секцию из БД
                await db.delete(section)
                logger.info(
                    f"Deleted expired section: {section.id} - {section.name}")

            await db.commit()
            logger.info(
                f"Successfully cleaned up {len(expired_sections)} expired sections")

        except Exception as e:
            logger.error(f"Error cleaning up expired sections: {e}")
            await db.rollback()


async def run_cleanup_task():
    """
    Запускает периодическую очистку просроченных секций
    Выполняется каждые 1 час
    """
    logger.info("Starting cleanup task for expired sections")

    while True:
        try:
            await cleanup_expired_sections()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

        # Ждать 1 час перед следующей проверкой
        await asyncio.sleep(3600)  # 3600 секунд = 1 час

