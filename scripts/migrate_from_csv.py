"""
Скрипт для миграции пользователей из CSV файла (report_542432_part1.csv) в PostgreSQL БД
"""
import asyncio
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Проверка зависимостей
try:
    from sqlalchemy import select, func, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
except ImportError as e:
    print("❌ Ошибка: модуль sqlalchemy не установлен!")
    print("\n📦 Установите зависимости:")
    print("   pip install -r requirements.txt")
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


def parse_date(date_str):
    """Парсинг даты из формата CSV"""
    if not date_str or date_str.strip() == '':
        return None
    
    try:
        # Формат: "2025-01-06 20:20:14 +0300"
        date_str = date_str.strip().strip('"')
        # Убираем временную зону для простоты
        date_part = date_str.split(' +')[0]
        return datetime.strptime(date_part, '%Y-%m-%d %H:%M:%S')
    except:
        return None


async def migrate_from_csv(
    csv_file_path: str,
    new_db_url: str = None,
    dry_run: bool = False
):
    """
    Переносит всех пользователей из CSV файла в PostgreSQL БД
    
    Args:
        csv_file_path: Путь к CSV файлу (например: report_542432_part1.csv)
        new_db_url: URL новой PostgreSQL базы данных (если None, используется settings.DATABASE_URL)
        dry_run: Если True, только показывает что будет сделано, не изменяет БД
    """
    if new_db_url is None:
        new_db_url = settings.DATABASE_URL
    
    # Проверяем существование CSV файла
    csv_path = Path(csv_file_path)
    if not csv_path.is_absolute():
        csv_path = root_dir / csv_path
    
    if not csv_path.exists():
        logger.error(f"❌ Файл CSV не найден: {csv_path}")
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"📁 CSV файл: {csv_path}")
    logger.info(f"🔗 PostgreSQL БД: {new_db_url.split('@')[1] if '@' in new_db_url else new_db_url}")
    
    if dry_run:
        logger.info("⚠️  РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут применены")
    
    # Подключаемся к PostgreSQL БД
    logger.info("🔌 Подключение к PostgreSQL БД...")
    try:
        new_engine = create_async_engine(new_db_url, echo=False, pool_pre_ping=True)
    except Exception as e:
        logger.error(f"❌ Ошибка при создании подключения к PostgreSQL: {e}")
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
        
        # Читаем CSV файл
        logger.info("📥 Чтение CSV файла...")
        users_from_csv = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # CSV с разделителем точка с запятой и кавычками
            reader = csv.DictReader(f, delimiter=';', quotechar='"')
            
            for row in reader:
                # Получаем telegram_id из колонки "Идентификатор внутри мессенджера"
                telegram_id_str = row.get('Идентификатор внутри мессенджера', '').strip().strip('"')
                
                if not telegram_id_str:
                    continue
                
                try:
                    telegram_id = int(telegram_id_str)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️  Пропущен пользователь с невалидным telegram_id: {telegram_id_str}")
                    continue
                
                # Получаем имя из колонки "Имя"
                name = row.get('Имя', '').strip().strip('"')
                
                # Парсим имя (может быть "Имя Фамилия" или просто "Имя")
                first_name = name.split()[0] if name else None
                last_name = ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else None
                
                # Получаем username из колонки "tg_username [client]"
                username = row.get('tg_username [client]', '').strip().strip('"')
                if username and username.startswith('@'):
                    username = username[1:]  # Убираем @
                if not username or username == 'Не указано':
                    username = None
                
                # Получаем даты
                created_at = parse_date(row.get('Дата первого контакта', ''))
                updated_at = parse_date(row.get('Дата последнего контакта', ''))
                
                if not created_at:
                    created_at = datetime.utcnow()
                if not updated_at:
                    updated_at = created_at
                
                users_from_csv.append({
                    'telegram_id': telegram_id,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'created_at': created_at,
                    'updated_at': updated_at
                })
        
        logger.info(f"✅ Найдено {len(users_from_csv)} пользователей в CSV файле")
        
        if len(users_from_csv) == 0:
            logger.warning("⚠️  В CSV файле нет пользователей для миграции")
            await new_engine.dispose()
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
            
            for csv_user in users_from_csv:
                telegram_id = csv_user['telegram_id']
                
                if telegram_id in existing_telegram_ids:
                    # Пользователь уже существует - обновляем данные
                    result = await new_session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    new_user = result.scalar_one_or_none()
                    
                    if new_user:
                        users_to_update.append((csv_user, new_user))
                    else:
                        users_to_add.append(csv_user)
                else:
                    # Новый пользователь - добавляем
                    users_to_add.append(csv_user)
            
            logger.info(f"\n📊 Статистика миграции:")
            logger.info(f"  • Новых пользователей для добавления: {len(users_to_add)}")
            logger.info(f"  • Пользователей для обновления: {len(users_to_update)}")
            
            if dry_run:
                logger.info("\n⚠️  Это был режим проверки. Для применения изменений запустите без --dry-run")
                await new_engine.dispose()
                return
            
            # Добавляем новых пользователей
            if users_to_add:
                logger.info(f"\n➕ Добавление {len(users_to_add)} новых пользователей...")
                added_count = 0
                for csv_user in users_to_add:
                    try:
                        new_user = User(
                            telegram_id=csv_user['telegram_id'],
                            username=csv_user['username'],
                            first_name=csv_user['first_name'],
                            last_name=csv_user['last_name'],
                            is_banned=False,
                            is_admin=False,
                            bonus_balance=0,
                            total_spent=0,
                            total_orders=0,
                            created_at=csv_user['created_at'],
                            updated_at=csv_user['updated_at']
                        )
                        new_session.add(new_user)
                        added_count += 1
                        
                        if added_count % 100 == 0:
                            await new_session.commit()
                            logger.info(f"   Обработано {added_count} пользователей...")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении пользователя {csv_user['telegram_id']}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Добавлено {added_count} пользователей")
            
            # Обновляем существующих пользователей
            if users_to_update:
                logger.info(f"\n🔄 Обновление {len(users_to_update)} пользователей...")
                updated_count = 0
                for csv_user, new_user in users_to_update:
                    try:
                        # Обновляем данные, сохраняя максимальные значения
                        new_user.username = csv_user['username'] or new_user.username
                        new_user.first_name = csv_user['first_name'] or new_user.first_name
                        new_user.last_name = csv_user['last_name'] or new_user.last_name
                        if csv_user['updated_at']:
                            new_user.updated_at = csv_user['updated_at']
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении пользователя {csv_user['telegram_id']}: {e}")
                
                await new_session.commit()
                logger.info(f"✅ Обновлено {updated_count} пользователей")
            
            # Финальная статистика
            result = await new_session.execute(
                select(func.count(User.id)).where(User.is_banned == False)
            )
            final_active = result.scalar_one()
            
            logger.info(f"\n✅ Миграция завершена!")
            logger.info(f"📊 Итого активных пользователей в PostgreSQL БД: {final_active}")
    
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции: {e}", exc_info=True)
        raise
    finally:
        await new_engine.dispose()


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Перенос пользователей из CSV файла в PostgreSQL')
    parser.add_argument(
        '--csv-file',
        type=str,
        default='report_542432_part1.csv',
        help='Путь к CSV файлу (по умолчанию: report_542432_part1.csv)'
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
    
    await migrate_from_csv(
        csv_file_path=args.csv_file,
        new_db_url=args.new_db_url,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())
