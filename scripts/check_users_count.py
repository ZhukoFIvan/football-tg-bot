"""
Скрипт для проверки количества пользователей в базе данных
"""
import asyncio
import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.session import AsyncSessionLocal
from core.db.models import User
from sqlalchemy import select, func


async def check_users_count():
    """Проверить количество пользователей в БД"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar()
        print(f"👥 Пользователей в базе данных: {count}")
        
        # Также покажем количество активных пользователей
        result_active = await session.execute(
            select(func.count(User.id)).where(User.is_banned == False)
        )
        active_count = result_active.scalar()
        print(f"✅ Активных пользователей (не забаненных): {active_count}")
        
        # Покажем количество админов
        result_admins = await session.execute(
            select(func.count(User.id)).where(User.is_admin == True)
        )
        admins_count = result_admins.scalar()
        print(f"👑 Администраторов: {admins_count}")


if __name__ == "__main__":
    asyncio.run(check_users_count())
