"""
Скрипт для переноса пользователей из SQLite БД (shop.db) в PostgreSQL БД
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Проверка зависимостей
try:
    import sqlite3
except ImportError:
    print("❌ Ошибка: модуль sqlite3 не найден!")
    print("💡 SQLite3 обычно встроен в Python. Проверьте установку Python.")
    sys.exit(1)

try:
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
except ImportError as e:
    print("❌ Ошибка: модуль sqlalchemy не установлен!")
    print("\n📦 Установите зависимости:")
    print("   1. Активируйте виртуальное окружение:")
    print("      source venv/bin/activate")
    print("   2. Установите зависимости:")
    print("      pip install -r requirements.txt")
    print("\n   Или установите только необходимые модули:")
    print("      pip install sqlalchemy asyncpg")
    print(f"\nДетали ошибки: {e}")
    sys.exit(1)

try:
    from core.db.models import User
    from core.config import settings
except ImportError as e:
    print(f"❌ Ошибка импорта из проекта: {e}")
    print("\n💡 Убедитесь, что:")
    print("   1. Вы находитесь в корневой директории проекта")
    print("   2. Все зависимости установлены")
    print("   3. Файл .env настроен правильно")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_from_sqlite(
    sqlite_db_path: str,
    new_db_url: str = None,
    dry_run: bool = False
):
    """
    Переносит всех пользователей из SQLite БД в PostgreSQL БД
    
    Args:
        sqlite_db_path: Путь к SQLite файлу (например: shop.db)
        new_db_url: URL новой PostgreSQL базы данных (если None, используется settings.DATABASE_URL)
        dry_run: Если True, только показывает что будет сделано, не изменяет БД
    """
    if new_db_url is None:
        new_db_url = settings.DATABASE_URL
    
    # Проверяем существование SQLite файла
    sqlite_path = Path(sqlite_db_path)
    
    # Если путь относительный, пробуем найти файл в разных местах
    if not sqlite_path.is_absolute():
        # В Docker контейнере проект монтируется в /app
        # Пробуем найти в корне проекта (относительно /app в Docker или корня проекта локально)
        root_dir = Path(__file__).parent.parent
        
        # Если мы в Docker (/app), используем /app, иначе корень проекта
        if Path('/app').exists() and Path('/app').is_dir():
            # Мы в Docker контейнере
            search_root = Path('/app')
        else:
            # Локально
            search_root = root_dir
        
        possible_paths = [
            search_root / sqlite_db_path,
            search_root / "apps" / sqlite_db_path,
            search_root / "apps" / "bot" / sqlite_db_path,
            search_root / "apps" / "api" / sqlite_db_path,
            root_dir / sqlite_db_path,  # Fallback
            root_dir / "apps" / sqlite_db_path,  # Fallback
        ]
        
        for possible_path in possible_paths:
            if possible_path.exists():
                sqlite_path = possible_path
                logger.info(f"📁 Найден файл БД: {sqlite_path}")
                break
        else:
            logger.error(f"❌ Файл SQLite БД не найден: {sqlite_db_path}")
            logger.error(f"   Проверены пути:")
            for pp in possible_paths:
                exists = "✅" if pp.exists() else "❌"
                logger.error(f"     {exists} {pp}")
            logger.error(f"   Текущая рабочая директория: {Path.cwd()}")
            raise FileNotFoundError(f"SQLite database file not found: {sqlite_db_path}")
    
    if not sqlite_path.exists():
        logger.error(f"❌ Файл SQLite БД не найден: {sqlite_path}")
        raise FileNotFoundError(f"SQLite database file not found: {sqlite_path}")
    
    logger.info(f"📁 SQLite БД: {sqlite_path}")
    logger.info(f"🔗 PostgreSQL БД: {new_db_url.split('@')[1] if '@' in new_db_url else new_db_url}")
    
    if dry_run:
        logger.info("⚠️  РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут применены")
    
    # Подключаемся к SQLite БД
    logger.info("🔌 Подключение к SQLite БД...")
    try:
        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    except Exception as e:
        logger.error(f"❌ Ошибка при подключении к SQLite БД: {e}")
        raise
    
    # Проверяем структуру SQLite БД
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not cursor.fetchone():
        logger.error("❌ Таблица 'users' не найдена в SQLite БД")
        sqlite_conn.close()
        raise ValueError("Table 'users' not found in SQLite database")
    
    # Получаем структуру таблицы users
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    logger.info(f"✅ Таблица 'users' найдена. Колонки: {', '.join(columns.keys())}")
    
    # Подключаемся к PostgreSQL БД
    logger.info("🔌 Подключение к PostgreSQL БД...")
    try:
        new_engine = create_async_engine(new_db_url, echo=False, pool_pre_ping=True)
    except Exception as e:
        logger.error(f"❌ Ошибка при создании подключения к PostgreSQL: {e}")
        sqlite_conn.close()
        raise
    
    new_session_factory = async_sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Проверяем подключение к PostgreSQL БД
        logger.info("🔍 Проверка подключения к PostgreSQL БД...")
        try:
            async with new_session_factory() as test_session:
                await test_session.execute(select(1))
            logger.info("✅ Подключение к PostgreSQL БД успешно")
        except Exception as e:
            logger.error(f"❌ Не удалось подключиться к PostgreSQL БД: {e}")
            raise
        
        # Получаем всех пользователей из SQLite БД
        logger.info("📥 Получение пользователей из SQLite БД...")
        # Проверяем наличие колонки is_banned
        cursor.execute("PRAGMA table_info(users)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        has_is_banned = 'is_banned' in column_names
        
        if has_is_banned:
            cursor.execute("SELECT * FROM users WHERE is_banned = 0")
        else:
            # Если колонки is_banned нет, получаем всех пользователей
            logger.info("⚠️  Колонка 'is_banned' не найдена, мигрируем всех пользователей")
            cursor.execute("SELECT * FROM users")
        
        old_users = cursor.fetchall()
        logger.info(f"✅ Найдено {len(old_users)} пользователей в SQLite БД")
        
        if len(old_users) == 0:
            logger.warning("⚠️  В SQLite БД нет активных пользователей для миграции")
            sqlite_conn.close()
            return
        
        # Получаем существующих пользователей из PostgreSQL БД (по telegram_id)
        async with new_session_factory() as new_session:
            logger.info("📥 Проверка существующих пользователей в PostgreSQL БД...")
            result = await new_session.execute(
                select(User.telegram_id)
            )
            existing_telegram_ids = {row[0] for row in result.all()}
            logger.info(f"✅ В PostgreSQL БД уже есть {len(existing_telegram_ids)} пользователей")
            
            # Статистика
            users_to_add = []
            users_to_update = []
            
            for old_user_row in old_users:
                # Преобразуем SQLite Row в словарь
                old_user = dict(old_user_row)
                # В shop.db колонка называется user_id, а не telegram_id
                telegram_id = old_user.get('telegram_id') or old_user.get('user_id') or old_user.get('id')
                
                if not telegram_id:
                    logger.warning(f"⚠️  Пропущен пользователь без telegram_id/user_id: {old_user}")
                    continue
                
                if telegram_id in existing_telegram_ids:
                    # Пользователь уже существует - обновляем данные
                    result = await new_session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    new_user = result.scalar_one_or_none()
                    
                    if new_user:
                        users_to_update.append((old_user, new_user))
                    else:
                        users_to_add.append(old_user)
                else:
                    # Новый пользователь - добавляем
                    users_to_add.append(old_user)
            
            logger.info(f"\n📊 Статистика миграции:")
            logger.info(f"  • Новых пользователей для добавления: {len(users_to_add)}")
            logger.info(f"  • Пользователей для обновления: {len(users_to_update)}")
            
            if dry_run:
                logger.info("\n⚠️  Это был режим проверки. Для применения изменений запустите без --dry-run")
                sqlite_conn.close()
                return
            
            # Добавляем новых пользователей
            if users_to_add:
                logger.info(f"\n➕ Добавление {len(users_to_add)} новых пользователей...")
                added_count = 0
                for old_user in users_to_add:
                    try:
                        # Получаем telegram_id (может быть user_id в shop.db)
                        tg_id = old_user.get('telegram_id') or old_user.get('user_id') or old_user.get('id')
                        
                        # Обработка created_at
                        created_at_val = old_user.get('created_at')
                        if created_at_val and isinstance(created_at_val, str):
                            try:
                                from datetime import datetime
                                created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S')
                            except:
                                from datetime import datetime
                                created_at_val = datetime.utcnow()
                        elif not created_at_val:
                            from datetime import datetime
                            created_at_val = datetime.utcnow()
                        
                        updated_at_val = old_user.get('updated_at') or created_at_val
                        if updated_at_val and isinstance(updated_at_val, str):
                            try:
                                from datetime import datetime
                                updated_at_val = datetime.strptime(updated_at_val, '%Y-%m-%d %H:%M:%S')
                            except:
                                updated_at_val = created_at_val
                        
                        new_user = User(
                            telegram_id=tg_id,
                            username=old_user.get('username') or None,
                            first_name=old_user.get('first_name') or None,
                            last_name=old_user.get('last_name') or None,
                            is_banned=bool(old_user.get('is_banned', False)) if 'is_banned' in old_user else False,
                            is_admin=bool(old_user.get('is_admin', False)) if 'is_admin' in old_user else False,
                            bonus_balance=int(old_user.get('bonus_balance', 0) or 0) if 'bonus_balance' in old_user else 0,
                            total_spent=float(old_user.get('total_spent', 0) or 0) if 'total_spent' in old_user else 0,
                            total_orders=int(old_user.get('total_orders', 0) or 0) if 'total_orders' in old_user else 0,
                            created_at=created_at_val,
                            updated_at=updated_at_val
                        )
                        new_session.add(new_user)
                        added_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении пользователя {old_user.get('telegram_id')}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Добавлено {added_count} пользователей")
            
            # Обновляем существующих пользователей
            if users_to_update:
                logger.info(f"\n🔄 Обновление {len(users_to_update)} пользователей...")
                updated_count = 0
                for old_user, new_user in users_to_update:
                    try:
                        # Обновляем данные, сохраняя максимальные значения
                        new_user.username = old_user.get('username') or new_user.username
                        new_user.first_name = old_user.get('first_name') or new_user.first_name
                        new_user.last_name = old_user.get('last_name') or new_user.last_name
                        new_user.is_banned = bool(old_user.get('is_banned', False))
                        new_user.is_admin = bool(old_user.get('is_admin', False)) or new_user.is_admin
                        # Сохраняем максимальные значения для бонусов и статистики
                        old_bonus = int(old_user.get('bonus_balance', 0) or 0)
                        old_spent = float(old_user.get('total_spent', 0) or 0)
                        old_orders = int(old_user.get('total_orders', 0) or 0)
                        new_user.bonus_balance = max(new_user.bonus_balance or 0, old_bonus)
                        new_user.total_spent = max(float(new_user.total_spent or 0), old_spent)
                        new_user.total_orders = max(new_user.total_orders or 0, old_orders)
                        if old_user.get('updated_at'):
                            new_user.updated_at = old_user.get('updated_at')
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении пользователя {old_user.get('telegram_id')}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Обновлено {updated_count} пользователей")
            
            # Финальная статистика
            result = await new_session.execute(
                select(func.count(User.id)).where(User.is_banned == False)
            )
            final_active = result.scalar_one()
            
            logger.info(f"\n✅ Миграция завершена!")
            logger.info(f"📊 Итого активных пользователей в PostgreSQL БД: {final_active}")
            logger.info(f"   (Все эти пользователи будут получать рассылки)")
    
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции: {e}", exc_info=True)
        raise
    finally:
        sqlite_conn.close()
        await new_engine.dispose()


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Перенос пользователей из SQLite БД в PostgreSQL')
    parser.add_argument(
        '--sqlite-db',
        type=str,
        default='shop.db',
        help='Путь к SQLite файлу (по умолчанию: shop.db)'
    )
    parser.add_argument(
        '--new-db-url',
        type=str,
        default=None,
        help='URL новой PostgreSQL базы данных (если не указан, используется DATABASE_URL из настроек)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим проверки без применения изменений'
    )
    
    args = parser.parse_args()
    
    await migrate_from_sqlite(
        sqlite_db_path=args.sqlite_db,
        new_db_url=args.new_db_url,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())
