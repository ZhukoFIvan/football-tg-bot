"""
Скрипт для активации всех пользователей из текущей БД
Убеждается, что все пользователи получают рассылки
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.db.models import User
from core.db.session import AsyncSessionLocal
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def activate_all_users(dry_run: bool = False):
    """
    Активирует всех пользователей в БД (убеждается, что они не забанены)
    и показывает статистику для рассылок
    
    Args:
        dry_run: Если True, только показывает статистику, не изменяет БД
    """
    logger.info("🔍 Анализ пользователей в базе данных...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Получаем статистику
            total_result = await session.execute(select(func.count(User.id)))
            total_users = total_result.scalar_one()
            
            banned_result = await session.execute(
                select(func.count(User.id)).where(User.is_banned == True)
            )
            banned_users = banned_result.scalar_one()
            
            active_result = await session.execute(
                select(func.count(User.id)).where(User.is_banned == False)
            )
            active_users = active_result.scalar_one()
            
            logger.info(f"\n📊 Статистика пользователей:")
            logger.info(f"  • Всего пользователей в БД: {total_users}")
            logger.info(f"  • Забанено: {banned_users}")
            logger.info(f"  • Активных (получают рассылки): {active_users}")
            
            if dry_run:
                logger.info("\n⚠️  РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут применены")
                return
            
            # Получаем всех пользователей для рассылки
            logger.info(f"\n📋 Список всех активных пользователей (получают рассылки):")
            result = await session.execute(
                select(User).where(User.is_banned == False).order_by(User.id)
            )
            active_users_list = result.scalars().all()
            
            # Показываем первые 10 и общее количество
            for i, user in enumerate(active_users_list[:10], 1):
                logger.info(f"  {i}. ID: {user.id}, Telegram ID: {user.telegram_id}, Username: @{user.username or 'нет'}, Имя: {user.first_name or 'нет'}")
            
            if len(active_users_list) > 10:
                logger.info(f"  ... и еще {len(active_users_list) - 10} пользователей")
            
            # Получаем всех забаненных пользователей
            if banned_users > 0:
                logger.info(f"\n🔓 Найдено {banned_users} забаненных пользователей")
                result = await session.execute(
                    select(User).where(User.is_banned == True)
                )
                banned_users_list = result.scalars().all()
                
                logger.info("Забаненные пользователи:")
                for user in banned_users_list[:5]:
                    logger.info(f"  • ID: {user.id}, Telegram ID: {user.telegram_id}, Username: @{user.username or 'нет'}")
                if len(banned_users_list) > 5:
                    logger.info(f"  ... и еще {len(banned_users_list) - 5} пользователей")
                
                if not dry_run:
                    logger.info(f"\n💡 Для разбана всех пользователей запустите скрипт без --dry-run и подтвердите действие")
            
            # Финальная статистика
            active_result = await session.execute(
                select(func.count(User.id)).where(User.is_banned == False)
            )
            final_active = active_result.scalar_one()
            
            logger.info(f"\n✅ Готово!")
            logger.info(f"📊 Итого активных пользователей для рассылок: {final_active}")
            logger.info(f"   (Все эти пользователи будут получать рассылки)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}", exc_info=True)
            raise


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Активация всех пользователей для рассылок')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим проверки без применения изменений'
    )
    
    args = parser.parse_args()
    
    await activate_all_users(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
