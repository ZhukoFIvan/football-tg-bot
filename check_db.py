"""
Скрипт для проверки содержимого SQLite БД (shop.db)
"""
import sqlite3
import sys
from pathlib import Path

# Путь к файлу БД
db_path = Path(__file__).parent / 'shop.db'

if not db_path.exists():
    print(f"❌ Файл БД не найден: {db_path}")
    print(f"   Текущая директория: {Path.cwd()}")
    sys.exit(1)

print(f"📁 Проверка БД: {db_path}")
print()

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Получаем список таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("📋 Таблицы в БД:")
for table in tables:
    print(f"  - {table}")

# Если есть таблица users, показываем структуру и количество записей
if 'users' in tables:
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\n📊 Структура таблицы 'users':")
    for col in columns:
        print(f"  • {col[1]} ({col[2]})")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\n👥 Всего пользователей: {count}")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
    active_count = cursor.fetchone()[0]
    print(f"✅ Активных пользователей (не забаненных): {active_count}")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_count = cursor.fetchone()[0]
    print(f"🚫 Забаненных пользователей: {banned_count}")
    
    # Показываем несколько примеров
    cursor.execute("SELECT telegram_id, username, first_name, is_banned, bonus_balance, total_spent FROM users LIMIT 5")
    print("\n📝 Примеры пользователей (первые 5):")
    for row in cursor.fetchall():
        banned_status = "🚫" if row[3] else "✅"
        print(f"  {banned_status} ID: {row[0]}, username: {row[1] or 'N/A'}, name: {row[2] or 'N/A'}, bonus: {row[4]}, spent: {row[5]}")
    
    print("\n💡 Для миграции этих пользователей в PostgreSQL используйте:")
    print("   docker compose exec api python scripts/migrate_from_sqlite.py --sqlite-db shop.db --dry-run")
else:
    print("\n⚠️  Таблица 'users' не найдена в БД")

conn.close()
