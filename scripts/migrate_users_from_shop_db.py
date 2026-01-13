"""
Скрипт для миграции пользователей из shop.db в текущую базу данных
"""
import sqlite3
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Проверка зависимостей
try:
    from sqlalchemy import text
except ImportError:
    print("❌ Ошибка: модуль sqlalchemy не установлен!")
    print("\n📦 Установите зависимости:")
    print("   pip install -r requirements.txt")
    print("\n   Или установите только необходимые модули:")
    print("   pip install sqlalchemy asyncpg")
    sys.exit(1)

try:
    from core.db.models import User
    from core.db.session import AsyncSessionLocal
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\n💡 Убедитесь, что:")
    print("   1. Вы находитесь в корневой директории проекта")
    print("   2. Все зависимости установлены: pip install -r requirements.txt")
    print("   3. Переменные окружения настроены (.env файл)")
    sys.exit(1)


def inspect_shop_db():
    """Проверить структуру shop.db"""
    db_path = Path(__file__).parent.parent / "shop.db"
    
    if not db_path.exists():
        print(f"❌ Файл {db_path} не найден!")
        return None
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Получить список таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    
    print("📋 Таблицы в shop.db:")
    for table in tables:
        print(f"  - {table}")
    
    # Найти таблицу с пользователями
    user_table = None
    for table in tables:
        if "user" in table.lower():
            user_table = table
            break
    
    if not user_table:
        print("❌ Таблица с пользователями не найдена!")
        conn.close()
        return None
    
    print(f"\n📊 Найдена таблица пользователей: {user_table}")
    
    # Получить структуру таблицы
    cursor.execute(f"PRAGMA table_info({user_table});")
    columns = cursor.fetchall()
    
    print("\n📋 Структура таблицы:")
    column_info = {}
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        column_info[col_name] = {
            'type': col_type,
            'not_null': not_null,
            'default': default_val,
            'pk': pk
        }
        print(f"  - {col_name}: {col_type} {'NOT NULL' if not_null else 'NULL'}")
    
    # Получить количество записей
    cursor.execute(f"SELECT COUNT(*) FROM {user_table};")
    count = cursor.fetchone()[0]
    print(f"\n👥 Всего пользователей: {count}")
    
    # Показать пример записи
    cursor.execute(f"SELECT * FROM {user_table} LIMIT 1;")
    sample = cursor.fetchone()
    if sample:
        print("\n📝 Пример записи:")
        for i, col_name in enumerate(column_info.keys()):
            print(f"  {col_name}: {sample[i]}")
    
    conn.close()
    return {
        'table_name': user_table,
        'columns': column_info,
        'count': count
    }


async def migrate_users():
    """Перенести пользователей из shop.db в текущую базу"""
    print("\n" + "="*60)
    print("🚀 Начало миграции пользователей")
    print("="*60)
    
    # Проверить структуру shop.db
    db_info = inspect_shop_db()
    if not db_info:
        return
    
    db_path = Path(__file__).parent.parent / "shop.db"
    shop_conn = sqlite3.connect(str(db_path))
    shop_cursor = shop_conn.cursor()
    
    # Получить все пользователи из shop.db
    shop_cursor.execute(f"SELECT * FROM {db_info['table_name']};")
    shop_users = shop_cursor.fetchall()
    column_names = list(db_info['columns'].keys())
    
    print(f"\n📥 Загружено {len(shop_users)} пользователей из shop.db")
    
    # Маппинг колонок для shop.db
    # Структура shop.db: user_id, username, first_name, created_at
    column_mapping = {}
    
    # Попробовать найти соответствия по названиям
    target_columns = {
        'telegram_id': ['telegram_id', 'tg_id', 'user_id', 'id'],
        'username': ['username', 'user_name'],
        'first_name': ['first_name', 'firstname', 'name'],
        'last_name': ['last_name', 'lastname', 'surname'],
        'created_at': ['created_at', 'created', 'date_created']
    }
    
    for target_col, possible_names in target_columns.items():
        for col_name in column_names:
            if col_name.lower() in [n.lower() for n in possible_names]:
                column_mapping[target_col] = col_name
                break
    
    print("\n🔗 Маппинг колонок:")
    for target, source in column_mapping.items():
        if source:
            print(f"  {target} <- {source}")
    
    # Подключиться к текущей базе данных
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    async with AsyncSessionLocal() as session:
        for shop_user in shop_users:
            try:
                # Создать словарь данных пользователя
                user_data = dict(zip(column_names, shop_user))
                
                # Проверить, существует ли пользователь с таким telegram_id
                telegram_id = None
                for key in ['telegram_id', 'tg_id', 'user_id', 'id']:
                    if key in user_data:
                        telegram_id = user_data[key]
                        break
                
                if not telegram_id:
                    print(f"⚠️  Пропущен пользователь: не найден telegram_id")
                    skipped_count += 1
                    continue
                
                # Проверить существование пользователя
                result = await session.execute(
                    text("SELECT id FROM users WHERE telegram_id = :tg_id"),
                    {"tg_id": telegram_id}
                )
                existing = result.fetchone()
                
                if existing:
                    print(f"⏭️  Пользователь {telegram_id} уже существует, пропускаем")
                    skipped_count += 1
                    continue
                
                # Получить значения из shop.db
                username_val = user_data.get(column_mapping.get('username')) if column_mapping.get('username') else None
                first_name_val = user_data.get(column_mapping.get('first_name')) if column_mapping.get('first_name') else None
                created_at_val = user_data.get(column_mapping.get('created_at')) if column_mapping.get('created_at') else None
                
                # Преобразовать created_at если это строка
                if created_at_val and isinstance(created_at_val, str):
                    try:
                        created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S')
                    except:
                        created_at_val = datetime.utcnow()
                elif not created_at_val:
                    created_at_val = datetime.utcnow()
                
                # Создать нового пользователя
                new_user = User(
                    telegram_id=telegram_id,
                    username=username_val if username_val else None,
                    first_name=first_name_val if first_name_val else None,
                    last_name=None,  # В shop.db нет last_name
                    is_banned=False,  # В shop.db нет is_banned
                    is_admin=False,  # В shop.db нет is_admin
                    bonus_balance=0,  # В shop.db нет bonus_balance
                    total_spent=0,  # В shop.db нет total_spent
                    total_orders=0,  # В shop.db нет total_orders
                    created_at=created_at_val,
                    updated_at=created_at_val
                )
                
                session.add(new_user)
                migrated_count += 1
                
                if migrated_count % 10 == 0:
                    await session.commit()
                    print(f"✅ Обработано {migrated_count} пользователей...")
                
            except Exception as e:
                print(f"❌ Ошибка при миграции пользователя: {e}")
                error_count += 1
                continue
        
        # Зафиксировать оставшиеся изменения
        await session.commit()
    
    shop_conn.close()
    
    print("\n" + "="*60)
    print("✅ Миграция завершена!")
    print("="*60)
    print(f"✅ Успешно мигрировано: {migrated_count}")
    print(f"⏭️  Пропущено (уже существуют): {skipped_count}")
    print(f"❌ Ошибок: {error_count}")
    print(f"📊 Всего обработано: {len(shop_users)}")


async def main():
    """Главная функция"""
    print("🔍 Проверка структуры shop.db...")
    print()
    
    # Сначала покажем структуру
    db_info = inspect_shop_db()
    
    if not db_info:
        print("\n❌ Не удалось прочитать shop.db")
        return
    
    # Спросить подтверждение
    print("\n" + "="*60)
    print("⚠️  ВНИМАНИЕ!")
    print("="*60)
    print("Этот скрипт перенесет пользователей из shop.db в текущую базу данных.")
    print("Пользователи с уже существующими telegram_id будут пропущены.")
    print("="*60)
    
    response = input("\nПродолжить миграцию? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y', 'да', 'д']:
        print("❌ Миграция отменена")
        return
    
    # Выполнить миграцию
    await migrate_users()


if __name__ == "__main__":
    asyncio.run(main())
