#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных тестовыми данными
"""
from core.db.models import Section, Category, Product, Badge, Banner
from core.db.session import AsyncSessionLocal
from sqlalchemy.orm import selectinload
from sqlalchemy import select, insert
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавить корневую директорию в путь
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


async def seed_data():
    """Заполнить базу данных тестовыми данными"""
    async with AsyncSessionLocal() as session:
        print("🌱 Начинаем заполнение базы данных...")

        # 1. Создать секции
        print("\n📂 Создаем секции...")
        sections_data = [
            {
                "name": "Хиты продаж",
                "route": "hits",
                "end_time": datetime.utcnow() + timedelta(days=7),  # 7 дней
                "sort_order": 1,
                "is_active": True
            },
            {
                "name": "Новинки",
                "route": "new",
                "end_time": datetime.utcnow() + timedelta(days=3),  # 3 дня
                "sort_order": 2,
                "is_active": True
            },
            {
                "name": "Скидки",
                "route": "sale",
                "end_time": datetime.utcnow() + timedelta(hours=48),  # 48 часов
                "sort_order": 3,
                "is_active": True
            }
        ]

        sections = []
        for data in sections_data:
            section = Section(**data)
            session.add(section)
            sections.append(section)

        await session.commit()
        print(f"✅ Создано {len(sections)} секций")

        # 2. Создать категории
        print("\n📁 Создаем категории...")
        categories_data = [
            {
                "title": "Action",
                "slug": "action",
                "description": "Динамичные игры с акцентом на реакцию и координацию",
                "sort_order": 1,
                "is_active": True
            },
            {
                "title": "RPG",
                "slug": "rpg",
                "description": "Ролевые игры с глубоким сюжетом и развитием персонажа",
                "sort_order": 2,
                "is_active": True
            },
            {
                "title": "Strategy",
                "slug": "strategy",
                "description": "Стратегические игры, требующие планирования и тактики",
                "sort_order": 3,
                "is_active": True
            },
            {
                "title": "Adventure",
                "slug": "adventure",
                "description": "Приключенческие игры с исследованием мира",
                "sort_order": 4,
                "is_active": True
            },
            {
                "title": "Shooter",
                "slug": "shooter",
                "description": "Шутеры от первого и третьего лица",
                "sort_order": 5,
                "is_active": True
            }
        ]

        categories = []
        for data in categories_data:
            category = Category(**data)
            session.add(category)
            categories.append(category)

        await session.commit()
        print(f"✅ Создано {len(categories)} категорий")

        # 3. Создать бейджи
        print("\n🏷️  Создаем бейджи...")
        badges_data = [
            {
                "title": "Новинка",
                "color": "#4CAF50",
                "text_color": "#FFFFFF",
                "is_active": True
            },
            {
                "title": "Хит продаж",
                "color": "#FF5722",
                "text_color": "#FFFFFF",
                "is_active": True
            },
            {
                "title": "Эксклюзив",
                "color": "#FFD700",
                "text_color": "#000000",
                "is_active": True
            },
            {
                "title": "Рекомендуем",
                "color": "#2196F3",
                "text_color": "#FFFFFF",
                "is_active": True
            }
        ]

        badges = []
        for data in badges_data:
            badge = Badge(**data)
            session.add(badge)
            badges.append(badge)

        await session.commit()
        print(f"✅ Создано {len(badges)} бейджей")

        # 4. Создать товары
        print("\n🎮 Создаем товары...")
        products_data = [
            # Action игры
            {
                "category_id": categories[0].id,  # Action
                "section_id": sections[0].id,  # Хиты продаж
                "badge_id": badges[1].id,  # Хит продаж
                "title": "Cyberpunk 2077",
                "slug": "cyberpunk-2077",
                "description": "Футуристическая RPG в открытом мире Night City с глубоким сюжетом и множеством выборов",
                "images": "[]",
                "price": 1999,
                "old_price": 2999,
                "promotion_text": "Скидка 33%",
                "currency": "RUB",
                "stock_count": 100,
                "is_active": True
            },
            {
                "category_id": categories[0].id,  # Action
                "section_id": sections[1].id,  # Новинки
                "badge_id": badges[0].id,  # Новинка
                "title": "Elden Ring",
                "slug": "elden-ring",
                "description": "Эпическая action-RPG от создателей Dark Souls с огромным открытым миром",
                "images": "[]",
                "price": 2499,
                "old_price": None,
                "promotion_text": None,
                "currency": "RUB",
                "stock_count": 50,
                "is_active": True
            },
            # RPG игры
            {
                "category_id": categories[1].id,  # RPG
                "section_id": sections[0].id,  # Хиты продаж
                "badge_id": badges[1].id,  # Хит продаж
                "title": "The Witcher 3: Wild Hunt",
                "slug": "witcher-3",
                "description": "Легендарная RPG о ведьмаке Геральте с захватывающим сюжетом и красивым миром",
                "images": "[]",
                "price": 899,
                "old_price": 1499,
                "promotion_text": "Мега скидка 40%",
                "currency": "RUB",
                "stock_count": 200,
                "is_active": True
            },
            {
                "category_id": categories[1].id,  # RPG
                "section_id": sections[2].id,  # Скидки
                "badge_id": badges[0].id,  # Новинка
                "title": "Baldur's Gate 3",
                "slug": "baldurs-gate-3",
                "description": "Масштабная RPG на основе Dungeons & Dragons с тактическими боями",
                "images": "[]",
                "price": 2199,
                "old_price": 2999,
                "promotion_text": "Скидка 27%",
                "currency": "RUB",
                "stock_count": 75,
                "is_active": True
            },
            # Strategy игры
            {
                "category_id": categories[2].id,  # Strategy
                "section_id": sections[2].id,  # Скидки
                "badge_id": None,
                "title": "Civilization VI",
                "slug": "civilization-6",
                "description": "Пошаговая стратегия о развитии цивилизации от древности до космической эры",
                "images": "[]",
                "price": 599,
                "old_price": 1199,
                "promotion_text": "Скидка 50%",
                "currency": "RUB",
                "stock_count": 150,
                "is_active": True
            },
            {
                "category_id": categories[2].id,  # Strategy
                "section_id": None,
                "badge_id": badges[3].id,  # Рекомендуем
                "title": "Total War: WARHAMMER III",
                "slug": "total-war-warhammer-3",
                "description": "Эпическая стратегия в фэнтезийной вселенной Warhammer",
                "images": "[]",
                "price": 1799,
                "old_price": None,
                "promotion_text": None,
                "currency": "RUB",
                "stock_count": 80,
                "is_active": True
            },
            # Adventure игры
            {
                "category_id": categories[3].id,  # Adventure
                "section_id": sections[1].id,  # Новинки
                "badge_id": badges[0].id,  # Новинка
                "title": "Red Dead Redemption 2",
                "slug": "rdr2",
                "description": "Приключенческий боевик о жизни на Диком Западе с потрясающей графикой",
                "images": "[]",
                "price": 1899,
                "old_price": None,
                "promotion_text": None,
                "currency": "RUB",
                "stock_count": 120,
                "is_active": True
            },
            {
                "category_id": categories[3].id,  # Adventure
                "section_id": sections[2].id,  # Скидки
                "badge_id": None,
                "title": "Assassin's Creed Valhalla",
                "slug": "ac-valhalla",
                "description": "Приключения викинга в Англии эпохи раннего средневековья",
                "images": "[]",
                "price": 1299,
                "old_price": 2499,
                "promotion_text": "Скидка 48%",
                "currency": "RUB",
                "stock_count": 90,
                "is_active": True
            },
            # Shooter игры
            {
                "category_id": categories[4].id,  # Shooter
                "section_id": sections[0].id,  # Хиты продаж
                "badge_id": badges[2].id,  # Эксклюзив
                "title": "Call of Duty: Modern Warfare III",
                "slug": "cod-mw3",
                "description": "Новейший шутер серии Call of Duty с динамичным мультиплеером",
                "images": "[]",
                "price": 2999,
                "old_price": None,
                "promotion_text": None,
                "currency": "RUB",
                "stock_count": 200,
                "is_active": True
            },
            {
                "category_id": categories[4].id,  # Shooter
                "section_id": sections[1].id,  # Новинки
                "badge_id": badges[0].id,  # Новинка
                "title": "Counter-Strike 2",
                "slug": "cs2",
                "description": "Легендарный тактический шутер в новом поколении на движке Source 2",
                "images": "[]",
                "price": 0,
                "old_price": None,
                "promotion_text": "Бесплатно!",
                "currency": "RUB",
                "stock_count": 999,
                "is_active": True
            },
            # Дополнительные товары
            {
                "category_id": categories[0].id,  # Action
                "section_id": sections[2].id,  # Скидки
                "badge_id": badges[1].id,  # Хит продаж
                "title": "Grand Theft Auto V",
                "slug": "gta-5",
                "description": "Культовый экшен в открытом мире Лос-Сантоса",
                "images": "[]",
                "price": 799,
                "old_price": 1499,
                "promotion_text": "Скидка 47%",
                "currency": "RUB",
                "stock_count": 300,
                "is_active": True
            },
            {
                "category_id": categories[1].id,  # RPG
                "section_id": None,
                "badge_id": badges[2].id,  # Эксклюзив
                "title": "Starfield",
                "slug": "starfield",
                "description": "Космическая RPG от создателей Skyrim и Fallout",
                "images": "[]",
                "price": 2799,
                "old_price": None,
                "promotion_text": None,
                "currency": "RUB",
                "stock_count": 60,
                "is_active": True
            }
        ]

        products = []
        for data in products_data:
            product = Product(**data)
            session.add(product)
            products.append(product)

        await session.commit()
        print(f"✅ Создано {len(products)} товаров")

        print("\n" + "="*50)
        print("🎉 База данных успешно заполнена!")
        print("="*50)
        print(f"\n📊 Статистика:")
        print(f"   • Секций: {len(sections)}")
        print(f"   • Категорий: {len(categories)}")
        print(f"   • Бейджей: {len(badges)}")
        print(f"   • Товаров: {len(products)}")
        print("\n✨ Готово!")


if __name__ == "__main__":
    asyncio.run(seed_data())
