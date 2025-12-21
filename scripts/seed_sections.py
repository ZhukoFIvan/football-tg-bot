"""
Скрипт для заполнения секций (максимум 3)
"""
from core.db.models import Section
from core.db.session import async_session
from sqlalchemy import delete
import asyncio
import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


async def clear_sections():
    """Очистить все секции"""
    async with async_session() as session:
        await session.execute(delete(Section))
        await session.commit()
        print("✅ Секции очищены")


async def seed_sections():
    """Заполнить секции"""
    async with async_session() as session:
        sections_data = [
            {
                "name": "Новогодняя распродажа",
                "image": None,  # Загрузите через админ-панель
                "route": "new-year-sale",
                "rest_time": 86400 * 7,  # 7 дней в секундах
                "sort_order": 1,
                "is_active": True
            },
            {
                "name": "Хиты продаж",
                "image": None,
                "route": "bestsellers",
                "rest_time": None,  # Без таймера
                "sort_order": 2,
                "is_active": True
            },
            {
                "name": "Новинки",
                "image": None,
                "route": "new-releases",
                "rest_time": None,
                "sort_order": 3,
                "is_active": True
            }
        ]

        for data in sections_data:
            section = Section(**data)
            session.add(section)

        await session.commit()
        print(f"✅ Создано {len(sections_data)} секций")


async def main():
    """Главная функция"""
    print("🌱 Заполнение секций...")
    print()

    # Очистить существующие секции
    await clear_sections()

    # Создать новые секции
    await seed_sections()

    print()
    print("✅ Готово!")
    print()
    print("📝 Следующие шаги:")
    print("1. Откройте Swagger: http://localhost:8000/docs")
    print("2. Авторизуйтесь как админ")
    print("3. Загрузите изображения для секций через:")
    print("   POST /admin/sections/{section_id}/image")
    print()
    print("🔍 Проверить секции:")
    print("   GET /sections")


if __name__ == "__main__":
    asyncio.run(main())
