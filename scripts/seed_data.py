"""
Скрипт для заполнения базы данных тестовыми данными
"""
from core.db.models import (
    User, Section, Category, Product, Badge, Banner, Order, OrderItem,
    Cart, CartItem, product_badges
)
from core.db.session import AsyncSessionLocal
from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


async def clear_database(db: AsyncSession):
    """Очистить все таблицы"""
    print("🗑️  Clearing database...")

    # Удаляем в правильном порядке (из-за FK)
    await db.execute(delete(OrderItem))
    await db.execute(delete(Order))
    await db.execute(delete(CartItem))
    await db.execute(delete(Cart))
    await db.execute(text("DELETE FROM product_badges"))
    await db.execute(delete(Product))
    await db.execute(delete(Category))
    await db.execute(delete(Section))
    await db.execute(delete(Badge))
    await db.execute(delete(Banner))
    await db.execute(delete(User))

    await db.commit()
    print("✅ Database cleared")


async def seed_users(db: AsyncSession):
    """Создать тестовых пользователей"""
    print("👥 Creating users...")

    users = [
        User(
            telegram_id=123456789,
            username="test_user",
            first_name="Тестовый",
            last_name="Пользователь",
            is_admin=True,
            is_banned=False
        ),
        User(
            telegram_id=987654321,
            username="john_doe",
            first_name="John",
            last_name="Doe",
            is_admin=False,
            is_banned=False
        ),
    ]

    for user in users:
        db.add(user)

    await db.commit()
    print(f"✅ Created {len(users)} users")


async def seed_badges(db: AsyncSession):
    """Создать бейджи"""
    print("🏷️  Creating badges...")

    badges = [
        Badge(title="Скидка 20%", color="#FF5722", text_color="#FFFFFF"),
        Badge(title="Скидка 30%", color="#E91E63", text_color="#FFFFFF"),
        Badge(title="Скидка 50%", color="#9C27B0", text_color="#FFFFFF"),
        Badge(title="Новинка", color="#2196F3", text_color="#FFFFFF"),
        Badge(title="Хит продаж", color="#4CAF50", text_color="#FFFFFF"),
        Badge(title="Топ", color="#FF9800", text_color="#FFFFFF"),
        Badge(title="Эксклюзив", color="#795548", text_color="#FFFFFF"),
    ]

    for badge in badges:
        db.add(badge)

    await db.commit()
    print(f"✅ Created {len(badges)} badges")

    return badges


async def seed_banners(db: AsyncSession):
    """Создать баннеры"""
    print("🎨 Creating banners...")

    banners = [
        Banner(
            title="Новогодняя распродажа",
            description="Скидки до 50% на все игры!",
            image="/uploads/banners/banner1.jpg",
            link="/category/action",
            sort_order=1,
            is_active=True
        ),
        Banner(
            title="Весенние скидки",
            description="Специальные предложения на RPG игры",
            image="/uploads/banners/banner2.jpg",
            link="/category/rpg",
            sort_order=2,
            is_active=True
        ),
        Banner(
            title="Летняя акция",
            description="Купи 2 игры - получи 3-ю в подарок",
            image="/uploads/banners/banner3.jpg",
            link="/",
            sort_order=3,
            is_active=True
        ),
    ]

    for banner in banners:
        db.add(banner)

    await db.commit()
    print(f"✅ Created {len(banners)} banners")


async def seed_catalog(db: AsyncSession, badges: list):
    """Создать каталог товаров"""
    print("📚 Creating catalog...")

    # Разделы
    sections_data = [
        {
            "title": "PC Games",
            "slug": "pc-games",
            "description": "Игры для ПК - Steam, Epic Games, Origin",
            "sort_order": 1
        },
        {
            "title": "Console Games",
            "slug": "console-games",
            "description": "Игры для PlayStation, Xbox, Nintendo",
            "sort_order": 2
        },
        {
            "title": "Gift Cards",
            "slug": "gift-cards",
            "description": "Подарочные карты для игровых сервисов",
            "sort_order": 3
        },
    ]

    sections = []
    for data in sections_data:
        section = Section(**data, is_active=True)
        db.add(section)
        sections.append(section)

    await db.flush()
    print(f"✅ Created {len(sections)} sections")

    # Категории для PC Games
    pc_categories_data = [
        {"title": "Action", "slug": "action",
            "description": "Экшн игры", "sort_order": 1},
        {"title": "RPG", "slug": "rpg", "description": "Ролевые игры", "sort_order": 2},
        {"title": "Strategy", "slug": "strategy",
            "description": "Стратегии", "sort_order": 3},
        {"title": "Shooter", "slug": "shooter",
            "description": "Шутеры", "sort_order": 4},
        {"title": "Adventure", "slug": "adventure",
            "description": "Приключения", "sort_order": 5},
    ]

    categories = []
    for data in pc_categories_data:
        category = Category(
            section_id=sections[0].id,
            **data,
            is_active=True
        )
        db.add(category)
        categories.append(category)

    # Категории для Console Games
    console_categories_data = [
        {"title": "PlayStation", "slug": "playstation",
            "description": "Игры для PS4/PS5", "sort_order": 1},
        {"title": "Xbox", "slug": "xbox",
            "description": "Игры для Xbox", "sort_order": 2},
        {"title": "Nintendo", "slug": "nintendo",
            "description": "Игры для Switch", "sort_order": 3},
    ]

    for data in console_categories_data:
        category = Category(
            section_id=sections[1].id,
            **data,
            is_active=True
        )
        db.add(category)
        categories.append(category)

    # Категории для Gift Cards
    giftcard_categories_data = [
        {"title": "Steam", "slug": "steam-cards",
            "description": "Steam Wallet", "sort_order": 1},
        {"title": "PlayStation", "slug": "psn-cards",
            "description": "PSN карты", "sort_order": 2},
        {"title": "Xbox", "slug": "xbox-cards",
            "description": "Xbox Gift Cards", "sort_order": 3},
    ]

    for data in giftcard_categories_data:
        category = Category(
            section_id=sections[2].id,
            **data,
            is_active=True
        )
        db.add(category)
        categories.append(category)

    await db.flush()
    print(f"✅ Created {len(categories)} categories")

    # Товары для Action категории
    action_products = [
        {
            "title": "Cyberpunk 2077",
            "slug": "cyberpunk-2077",
            "description": "Открытый мир будущего в Night City. RPG от создателей Ведьмака.",
            "price": 1999.00,
            "old_price": 2999.00,
            "stock_count": 50,
            "badge_ids": [0, 3]  # Скидка 20%, Новинка
        },
        {
            "title": "Grand Theft Auto V",
            "slug": "gta-5",
            "description": "Легендарный экшен в открытом мире Лос-Сантоса.",
            "price": 1499.00,
            "old_price": None,
            "stock_count": 100,
            "badge_ids": [4]  # Хит продаж
        },
        {
            "title": "Red Dead Redemption 2",
            "slug": "rdr2",
            "description": "Эпическое приключение на Диком Западе.",
            "price": 2499.00,
            "old_price": 3499.00,
            "stock_count": 30,
            "badge_ids": [1, 4]  # Скидка 30%, Хит продаж
        },
        {
            "title": "Assassin's Creed Valhalla",
            "slug": "ac-valhalla",
            "description": "Станьте легендарным викингом в эпоху завоеваний.",
            "price": 1799.00,
            "old_price": 2999.00,
            "stock_count": 45,
            "badge_ids": [0]  # Скидка 20%
        },
    ]

    # Товары для RPG категории
    rpg_products = [
        {
            "title": "The Witcher 3: Wild Hunt",
            "slug": "witcher-3",
            "description": "Легендарная RPG о Геральте из Ривии. GOTY Edition.",
            "price": 899.00,
            "old_price": 1499.00,
            "stock_count": 80,
            "badge_ids": [2, 4]  # Скидка 50%, Хит продаж
        },
        {
            "title": "Elden Ring",
            "slug": "elden-ring",
            "description": "Новая игра от создателей Dark Souls. Открытый мир фэнтези.",
            "price": 2999.00,
            "old_price": None,
            "stock_count": 25,
            "badge_ids": [3, 5]  # Новинка, Топ
        },
        {
            "title": "Baldur's Gate 3",
            "slug": "baldurs-gate-3",
            "description": "Легендарная RPG возвращается. Основано на D&D.",
            "price": 2499.00,
            "old_price": None,
            "stock_count": 40,
            "badge_ids": [3, 5]  # Новинка, Топ
        },
        {
            "title": "Skyrim Special Edition",
            "slug": "skyrim-se",
            "description": "Классическая RPG в мире Тамриэля. Улучшенная версия.",
            "price": 799.00,
            "old_price": 1299.00,
            "stock_count": 120,
            "badge_ids": [2, 4]  # Скидка 50%, Хит продаж
        },
    ]

    # Товары для Strategy категории
    strategy_products = [
        {
            "title": "Civilization VI",
            "slug": "civ-6",
            "description": "Постройте империю, которая выдержит испытание временем.",
            "price": 1299.00,
            "old_price": 1999.00,
            "stock_count": 60,
            "badge_ids": [0]  # Скидка 20%
        },
        {
            "title": "Total War: Warhammer III",
            "slug": "tw-warhammer-3",
            "description": "Эпические битвы в мире Warhammer Fantasy.",
            "price": 2199.00,
            "old_price": None,
            "stock_count": 35,
            "badge_ids": [3]  # Новинка
        },
    ]

    # Товары для Shooter категории
    shooter_products = [
        {
            "title": "Call of Duty: Modern Warfare III",
            "slug": "cod-mw3",
            "description": "Новейший шутер в легендарной серии COD.",
            "price": 3499.00,
            "old_price": None,
            "stock_count": 20,
            "badge_ids": [3, 5]  # Новинка, Топ
        },
        {
            "title": "Counter-Strike 2",
            "slug": "cs2",
            "description": "Легендарный тактический шутер. Новое поколение.",
            "price": 0.00,
            "old_price": None,
            "stock_count": 999,
            "badge_ids": [4]  # Хит продаж
        },
    ]

    # Подарочные карты
    giftcard_products = [
        {
            "title": "Steam Wallet 500₽",
            "slug": "steam-500",
            "description": "Пополнение Steam кошелька на 500 рублей.",
            "price": 500.00,
            "old_price": None,
            "stock_count": 200,
            "badge_ids": []
        },
        {
            "title": "Steam Wallet 1000₽",
            "slug": "steam-1000",
            "description": "Пополнение Steam кошелька на 1000 рублей.",
            "price": 1000.00,
            "old_price": None,
            "stock_count": 150,
            "badge_ids": []
        },
        {
            "title": "PlayStation Plus 1 месяц",
            "slug": "ps-plus-1m",
            "description": "Подписка PlayStation Plus на 1 месяц.",
            "price": 699.00,
            "old_price": None,
            "stock_count": 100,
            "badge_ids": []
        },
    ]

    # Создать все товары
    all_products = [
        (categories[0].id, action_products),      # Action
        (categories[1].id, rpg_products),         # RPG
        (categories[2].id, strategy_products),    # Strategy
        (categories[3].id, shooter_products),     # Shooter
        (categories[8].id, giftcard_products),    # Steam cards
    ]

    products_count = 0
    for category_id, products_list in all_products:
        for product_data in products_list:
            badge_ids = product_data.pop("badge_ids", [])

            product = Product(
                category_id=category_id,
                currency="RUB",
                is_active=True,
                **product_data
            )

            # Добавить бейджи через relationship
            product_badges_list = []
            for badge_idx in badge_ids:
                if badge_idx < len(badges):
                    product_badges_list.append(badges[badge_idx])

            product.badges = product_badges_list

            db.add(product)
            products_count += 1

    await db.commit()
    print(f"✅ Created {products_count} products")


async def main():
    """Главная функция"""
    print("🌱 Starting database seeding...")
    print()

    async with AsyncSessionLocal() as db:
        # Очистить БД
        await clear_database(db)
        print()

        # Создать данные
        await seed_users(db)
        badges = await seed_badges(db)
        await seed_banners(db)
        await seed_catalog(db, badges)

        print()
        print("✨ Database seeding completed!")
        print()
        print("📊 Summary:")
        print("  - 2 users (1 admin)")
        print("  - 7 badges")
        print("  - 3 banners")
        print("  - 3 sections")
        print("  - 11 categories")
        print("  - 15+ products")
        print()
        print("🔑 Test admin credentials:")
        print("  Telegram ID: 123456789")
        print("  Username: @test_user")


if __name__ == "__main__":
    asyncio.run(main())
