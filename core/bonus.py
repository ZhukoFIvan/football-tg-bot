"""
Логика бонусной системы
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db.models import User, BonusTransaction, Order


class BonusSystem:
    """Класс для работы с бонусной системой"""

    # Настройки бонусной системы
    BONUS_RATE = 0.05  # 5% от суммы покупки возвращается бонусами
    MAX_BONUS_USAGE_PERCENT = 0.50  # Максимум 50% от суммы можно оплатить бонусами
    BONUS_TO_RUBLE = 1  # 1 бонус = 1 рубль

    # Пороги для начисления бонусных рублей (согласно карте)
    BONUS_MILESTONES = {
        1: 50,       # За 1-ю покупку - 50 ₽ на баланс
        3: 75,       # За 3-ю покупку - 75 ₽ на баланс
        5: 0,        # За 5-ю покупку - Усилитель В (выдается владельцем)
        10: 50,      # За 10-ю покупку - 50 ₽ на баланс
        15: 75,      # За 15-ю покупку - 75 ₽ на баланс
        # За 20-ю покупку - Секретный подарок (выдается владельцем)
        20: 0,
        30: 200,     # За 30-ю покупку - 200 ₽ на баланс
        40: 250,     # За 40-ю покупку - 250 ₽ на баланс
        50: 0,       # За 50-ю покупку - Любой абонемент (выдается владельцем)
        60: 350,     # За 60-ю покупку - 350 ₽ на баланс
        70: 400,     # За 70-ю покупку - 400 ₽ на баланс
        80: 450,     # За 80-ю покупку - 450 ₽ на баланс
        90: 500,     # За 90-ю покупку - 500 ₽ на баланс
        # За 100-ю покупку - 20 000 FC Points (выдается владельцем)
        100: 0,
    }

    @staticmethod
    async def calculate_earned_bonuses(order_amount: Decimal, user: User) -> int:
        """
        Рассчитать количество бонусных рублей к начислению

        Args:
            order_amount: Сумма заказа (не используется, но оставлен для совместимости)
            user: Пользователь

        Returns:
            Количество бонусных рублей к начислению
        """
        # Бонус за достижение порога (только бонусные рубли, не FC Points)
        next_order_count = user.total_orders + 1
        milestone_bonus = BonusSystem.BONUS_MILESTONES.get(next_order_count, 0)

        return milestone_bonus

    @staticmethod
    async def calculate_max_bonus_usage(order_amount: Decimal) -> int:
        """
        Рассчитать максимальное количество бонусов, которое можно использовать

        Args:
            order_amount: Сумма заказа

        Returns:
            Максимальное количество бонусов
        """
        max_bonus_amount = float(order_amount) * \
            BonusSystem.MAX_BONUS_USAGE_PERCENT
        return int(max_bonus_amount / BonusSystem.BONUS_TO_RUBLE)

    @staticmethod
    async def apply_bonuses(
        user: User,
        order_amount: Decimal,
        bonus_to_use: int,
        db: AsyncSession
    ) -> tuple[Decimal, int, int]:
        """
        Применить бонусы к заказу

        Args:
            user: Пользователь
            order_amount: Сумма заказа
            bonus_to_use: Количество бонусов к использованию
            db: Сессия БД

        Returns:
            (итоговая_сумма, использовано_бонусов, начислено_бонусов)
        """
        # Проверить доступность бонусов
        if bonus_to_use > user.bonus_balance:
            bonus_to_use = user.bonus_balance

        # Проверить максимальное использование
        max_bonus = await BonusSystem.calculate_max_bonus_usage(order_amount)
        if bonus_to_use > max_bonus:
            bonus_to_use = max_bonus

        # Рассчитать итоговую сумму
        bonus_discount = Decimal(bonus_to_use * BonusSystem.BONUS_TO_RUBLE)
        final_amount = order_amount - bonus_discount

        # Рассчитать начисление бонусов (от итоговой суммы)
        earned_bonuses = await BonusSystem.calculate_earned_bonuses(final_amount, user)

        return final_amount, bonus_to_use, earned_bonuses

    @staticmethod
    async def process_order_bonuses(
        user: User,
        order: Order,
        db: AsyncSession
    ):
        """
        Обработать бонусы после оплаты заказа

        Args:
            user: Пользователь
            order: Заказ
            db: Сессия БД
        """
        # Списать использованные бонусы
        if order.bonus_used > 0:
            user.bonus_balance -= order.bonus_used

            # Создать транзакцию списания
            spent_transaction = BonusTransaction(
                user_id=user.id,
                order_id=order.id,
                amount=-order.bonus_used,
                type="spent",
                description=f"Списание бонусов за заказ #{order.id}"
            )
            db.add(spent_transaction)

        # Начислить заработанные бонусы
        if order.bonus_earned > 0:
            user.bonus_balance += order.bonus_earned

            # Создать транзакцию начисления
            earned_transaction = BonusTransaction(
                user_id=user.id,
                order_id=order.id,
                amount=order.bonus_earned,
                type="earned",
                description=f"Начисление бонусов за заказ #{order.id}"
            )
            db.add(earned_transaction)

        # Обновить статистику пользователя
        user.total_spent += order.final_amount
        user.total_orders += 1

        await db.commit()

    @staticmethod
    async def get_next_milestone(user: User) -> Optional[tuple[int, int, str]]:
        """
        Получить следующий порог для начисления бонусов

        Args:
            user: Пользователь

        Returns:
            (количество_заказов, количество_бонусов, описание) или None
        """
        next_order = user.total_orders + 1

        # Описания наград
        milestone_descriptions = {
            1: "50 ₽ на баланс",
            3: "75 ₽ на баланс",
            5: "Усилитель В",
            10: "50 ₽ на баланс",
            15: "75 ₽ на баланс",
            20: "Секретный подарок",
            30: "200 ₽ на баланс",
            40: "250 ₽ на баланс",
            50: "Любой абонемент",
            60: "350 ₽ на баланс",
            70: "400 ₽ на баланс",
            80: "450 ₽ на баланс",
            90: "500 ₽ на баланс",
            100: "20 000 FC Points",
        }

        # Найти ближайший порог
        for milestone, bonus in sorted(BonusSystem.BONUS_MILESTONES.items()):
            if milestone >= next_order:
                description = milestone_descriptions.get(
                    milestone, f"{bonus} ₽")
                return (milestone, bonus, description)

        return None
