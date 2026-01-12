"""
Скрипт для переноса пользователей из старой БД в новую БД
Старый и новый бот используют один и тот же токен, но разные БД
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.db.models import User
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_from_old_bot(
    old_db_url: str,
    new_db_url: str = None,
    dry_run: bool = False
):
    """
    Переносит всех пользователей из старой БД в новую БД
    
    Args:
        old_db_url: URL старой базы данных (например: postgresql+asyncpg://user:pass@host:port/old_db)
        new_db_url: URL новой базы данных (если None, используется settings.DATABASE_URL)
        dry_run: Если True, только показывает что будет сделано, не изменяет БД
    """
    if new_db_url is None:
        new_db_url = settings.DATABASE_URL
    
    # Показываем информацию о БД (скрываем пароль)
    old_db_display = old_db_url.split('@')[1] if '@' in old_db_url else old_db_url
    new_db_display = new_db_url.split('@')[1] if '@' in new_db_url else new_db_url
    logger.info(f"🔗 Старая БД: {old_db_display}")
    logger.info(f"🔗 Новая БД: {new_db_display}")
    
    if dry_run:
        logger.info("⚠️  РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут применены")
    
    # Создаем подключения к БД
    logger.info("🔌 Подключение к базам данных...")
    try:
        old_engine = create_async_engine(old_db_url, echo=False, pool_pre_ping=True)
        new_engine = create_async_engine(new_db_url, echo=False, pool_pre_ping=True)
    except Exception as e:
        logger.error(f"❌ Ошибка при создании подключений: {e}")
        raise
    
    old_session_factory = async_sessionmaker(old_engine, class_=AsyncSession, expire_on_commit=False)
    new_session_factory = async_sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Проверяем подключение к старой БД
        logger.info("🔍 Проверка подключения к старой БД...")
        try:
            async with old_session_factory() as test_session:
                await test_session.execute(select(1))
            logger.info("✅ Подключение к старой БД успешно")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Не удалось подключиться к старой БД!")
            logger.error(f"   Ошибка: {error_msg}")
            logger.error("")
            logger.error("💡 Возможные решения:")
            logger.error("   1. Проверьте правильность URL старой БД")
            if "name resolution" in error_msg.lower() or "gaierror" in error_msg.lower():
                logger.error("   2. ❗ ПРОБЛЕМА: Хост не может быть разрешен (не найден)")
                logger.error("      Если старая БД на том же сервере, используйте:")
                logger.error("      - 'postgres' (имя контейнера PostgreSQL в Docker)")
                logger.error("      - 'localhost' или '127.0.0.1' (если БД на хосте)")
                logger.error("")
                logger.error("   Примеры правильных URL:")
                logger.error("     postgresql+asyncpg://postgres:password@postgres:5432/old_database")
                logger.error("     postgresql+asyncpg://postgres:password@localhost:5432/old_database")
            else:
                logger.error("   2. Проверьте доступность хоста и порта")
                logger.error("   3. Убедитесь, что старая БД запущена")
            logger.error("   4. Проверьте правильность имени базы данных")
            logger.error("   5. Проверьте правильность логина и пароля")
            raise
        
        # Проверяем подключение к новой БД
        logger.info("🔍 Проверка подключения к новой БД...")
        try:
            async with new_session_factory() as test_session:
                await test_session.execute(select(1))
            logger.info("✅ Подключение к новой БД успешно")
        except Exception as e:
            logger.error(f"❌ Не удалось подключиться к новой БД: {e}")
            raise
        
        async with old_session_factory() as old_session, new_session_factory() as new_session:
            # Получаем всех пользователей из старой БД
            logger.info("📥 Получение пользователей из старой БД...")
            result = await old_session.execute(
                select(User).where(User.is_banned == False)
            )
            old_users = result.scalars().all()
            logger.info(f"✅ Найдено {len(old_users)} активных пользователей в старой БД")
            
            # Получаем существующих пользователей из новой БД (по telegram_id)
            logger.info("📥 Проверка существующих пользователей в новой БД...")
            result = await new_session.execute(
                select(User.telegram_id)
            )
            existing_telegram_ids = {row[0] for row in result.all()}
            logger.info(f"✅ В новой БД уже есть {len(existing_telegram_ids)} пользователей")
            
            # Статистика
            users_to_add = []
            users_to_update = []
            users_skipped = []
            
            for old_user in old_users:
                if old_user.telegram_id in existing_telegram_ids:
                    # Пользователь уже существует - обновляем данные
                    result = await new_session.execute(
                        select(User).where(User.telegram_id == old_user.telegram_id)
                    )
                    new_user = result.scalar_one_or_none()
                    
                    if new_user:
                        # Обновляем данные, сохраняя максимальные значения
                        users_to_update.append((old_user, new_user))
                    else:
                        users_to_add.append(old_user)
                else:
                    # Новый пользователь - добавляем
                    users_to_add.append(old_user)
            
            logger.info(f"\n📊 Статистика миграции:")
            logger.info(f"  • Новых пользователей для добавления: {len(users_to_add)}")
            logger.info(f"  • Пользователей для обновления: {len(users_to_update)}")
            logger.info(f"  • Пользователей пропущено (уже актуальны): {len(users_skipped)}")
            
            if dry_run:
                logger.info("\n⚠️  Это был режим проверки. Для применения изменений запустите без --dry-run")
                return
            
            # Добавляем новых пользователей
            if users_to_add:
                logger.info(f"\n➕ Добавление {len(users_to_add)} новых пользователей...")
                added_count = 0
                for old_user in users_to_add:
                    try:
                        new_user = User(
                            telegram_id=old_user.telegram_id,
                            username=old_user.username,
                            first_name=old_user.first_name or "",
                            last_name=old_user.last_name or "",
                            is_banned=old_user.is_banned,
                            is_admin=old_user.is_admin,
                            bonus_balance=old_user.bonus_balance or 0,
                            total_spent=old_user.total_spent or 0,
                            total_orders=old_user.total_orders or 0,
                            created_at=old_user.created_at,
                            updated_at=old_user.updated_at or old_user.created_at
                        )
                        new_session.add(new_user)
                        added_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении пользователя {old_user.telegram_id}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Добавлено {added_count} пользователей")
            
            # Обновляем существующих пользователей
            if users_to_update:
                logger.info(f"\n🔄 Обновление {len(users_to_update)} пользователей...")
                updated_count = 0
                for old_user, new_user in users_to_update:
                    try:
                        # Обновляем данные, сохраняя максимальные значения
                        new_user.username = old_user.username or new_user.username
                        new_user.first_name = old_user.first_name or new_user.first_name
                        new_user.last_name = old_user.last_name or new_user.last_name
                        new_user.is_banned = old_user.is_banned
                        new_user.is_admin = old_user.is_admin or new_user.is_admin
                        # Сохраняем максимальные значения для бонусов и статистики
                        new_user.bonus_balance = max(new_user.bonus_balance or 0, old_user.bonus_balance or 0)
                        new_user.total_spent = max(new_user.total_spent or 0, old_user.total_spent or 0)
                        new_user.total_orders = max(new_user.total_orders or 0, old_user.total_orders or 0)
                        if old_user.updated_at:
                            new_user.updated_at = old_user.updated_at
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении пользователя {old_user.telegram_id}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Обновлено {updated_count} пользователей")
            
            # Финальная статистика
            result = await new_session.execute(
                select(func.count(User.id)).where(User.is_banned == False)
            )
            final_active = result.scalar_one()
            
            logger.info(f"\n✅ Миграция завершена!")
            logger.info(f"📊 Итого активных пользователей в новой БД: {final_active}")
            logger.info(f"   (Все эти пользователи будут получать рассылки)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции: {e}", exc_info=True)
        raise
    finally:
        await old_engine.dispose()
        await new_engine.dispose()


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Перенос пользователей из старой БД в новую')
    parser.add_argument(
        '--old-db-url',
        type=str,
        required=True,
        help='URL старой базы данных (например: postgresql+asyncpg://user:pass@host:port/old_db)'
    )
    parser.add_argument(
        '--new-db-url',
        type=str,
        default=None,
        help='URL новой базы данных (если не указан, используется DATABASE_URL из настроек)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим проверки без применения изменений'
    )
    
    args = parser.parse_args()
    
    await migrate_from_old_bot(
        old_db_url=args.old_db_url,
        new_db_url=args.new_db_url,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())
