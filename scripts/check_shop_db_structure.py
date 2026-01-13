"""
Скрипт для проверки структуры shop.db
Только просмотр, без изменений в базе данных
"""
import sqlite3
import sys
from pathlib import Path

# Путь к shop.db
db_path = Path(__file__).parent.parent / "shop.db"

if not db_path.exists():
    print(f"❌ Файл {db_path} не найден!")
    sys.exit(1)

print("="*60)
print("🔍 ПРОВЕРКА СТРУКТУРЫ shop.db")
print("="*60)
print()

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Получить список таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📋 Таблицы в shop.db:")
print("-" * 60)
for table in tables:
    table_name = table[0]
    print(f"\n📊 Таблица: {table_name}")
    
    # Получить структуру таблицы
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print("  Колонки:")
    column_names = []
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        column_names.append(col_name)
        nullable = "NULL" if not_null == 0 else "NOT NULL"
        pk_mark = " [PK]" if pk else ""
        default_str = f" DEFAULT {default_val}" if default_val else ""
        print(f"    - {col_name}: {col_type} ({nullable}){default_str}{pk_mark}")
    
    # Получить количество записей
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"  📊 Записей: {count}")
    
    # Показать первые несколько записей для таблицы users (если есть)
    if "user" in table_name.lower() and count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        rows = cursor.fetchall()
        if rows:
            print("  📝 Примеры записей (первые 3):")
            for idx, row in enumerate(rows, 1):
                print(f"    Запись {idx}:")
                for col_name, value in zip(column_names, row):
                    print(f"      {col_name}: {value}")
                print()

# Найти таблицу с пользователями
print("\n" + "="*60)
print("🔍 ПОИСК ТАБЛИЦЫ С ПОЛЬЗОВАТЕЛЯМИ")
print("="*60)

user_table = None
for table in tables:
    table_name = table[0]
    if "user" in table_name.lower():
        user_table = table_name
        print(f"\n✅ Найдена таблица: {user_table}")
        
        # Получить все данные для анализа
        cursor.execute(f"SELECT * FROM {user_table} LIMIT 5;")
        sample_rows = cursor.fetchall()
        
        cursor.execute(f"PRAGMA table_info({user_table});")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        print(f"\n📊 Всего пользователей: {count}")
        print(f"\n📋 Структура таблицы {user_table}:")
        for col in columns_info:
            col_id, col_name, col_type, not_null, default_val, pk = col
            print(f"  - {col_name}: {col_type}")
        
        if sample_rows:
            print(f"\n📝 Примеры записей (первые {len(sample_rows)}):")
            for idx, row in enumerate(sample_rows, 1):
                print(f"\n  Пользователь {idx}:")
                for col_name, value in zip(column_names, row):
                    print(f"    {col_name}: {value}")
        break

if not user_table:
    print("⚠️  Таблица с пользователями не найдена!")
    print("   Ищите таблицы, содержащие 'user' в названии")

conn.close()

print("\n" + "="*60)
print("✅ Проверка завершена")
print("="*60)
print("\n💡 Для миграции данных запустите:")
print("   python scripts/migrate_users_from_shop_db.py")
