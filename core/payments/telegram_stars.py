"""
Оплата через Telegram Stars
https://core.telegram.org/bots/payments
"""
from typing import Dict, Optional
from decimal import Decimal
from aiogram import Bot
from aiogram.types import LabeledPrice

from core.payments.base import PaymentProvider


class TelegramStarsProvider(PaymentProvider):
    """Провайдер оплаты через Telegram Stars"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int
    ) -> Dict:
        """
        Создать invoice для оплаты через Telegram Stars

        TODO: Реализовать создание invoice через bot.send_invoice()

        Документация:
        https://core.telegram.org/bots/api#sendinvoice
        """
        # Конвертировать сумму в копейки/минимальные единицы
        amount_cents = int(amount * 100)

        # Создать invoice
        # await self.bot.send_invoice(
        #     chat_id=user_id,
        #     title=f"Заказ #{order_id}",
        #     description=description,
        #     payload=f"order_{order_id}",
        #     provider_token="",  # Для Stars не нужен
        #     currency="XTR",  # Telegram Stars
        #     prices=[
        #         LabeledPrice(label="Заказ", amount=amount_cents)
        #     ]
        # )

        return {
            "payment_id": f"stars_{order_id}",
            "payment_url": None,  # Invoice отправляется в чат
            "status": "pending"
        }

    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа

        TODO: Реализовать проверку через webhook или polling
        """
        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": Decimal(0)
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """Отменить платеж (для Stars нельзя отменить после создания)"""
        return False

    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Вернуть деньги

        TODO: Реализовать возврат через bot.refund_star_payment()
        """
        return {
            "refund_id": f"refund_{payment_id}",
            "status": "pending",
            "amount": amount or Decimal(0)
        }
