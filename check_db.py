import sqlite3

conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

# Получаем список таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("Таблицы в БД:")
for table in tables:
    print(f"  - {table}")

# Если есть таблица users, показываем структуру и количество записей
if 'users' in tables:
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\nСтруктура таблицы 'users':")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\nКоличество пользователей: {count}")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
    active_count = cursor.fetchone()[0]
    print(f"Активных пользователей (не забаненных): {active_count}")
    
    # Показываем несколько примеров
    cursor.execute("SELECT telegram_id, username, first_name, is_banned, bonus_balance, total_spent FROM users LIMIT 5")
    print("\nПримеры пользователей:")
    for row in cursor.fetchall():
        print(f"  ID: {row[0]}, username: {row[1]}, name: {row[2]}, banned: {row[3]}, bonus: {row[4]}, spent: {row[5]}")

conn.close()
