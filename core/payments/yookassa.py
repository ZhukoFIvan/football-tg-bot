"""
Оплата через ЮKassa (Yookassa)
https://yookassa.ru/developers/api
"""
from typing import Dict, Optional
from decimal import Decimal
import uuid

from core.payments.base import PaymentProvider


class YookassaProvider(PaymentProvider):
    """Провайдер оплаты через ЮKassa"""

    def __init__(self, shop_id: str, secret_key: str):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_url = "https://api.yookassa.ru/v3"

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int
    ) -> Dict:
        """
        Создать платеж в ЮKassa

        TODO: Реализовать через HTTP запрос к API ЮKassa

        Пример:
        POST https://api.yookassa.ru/v3/payments
        Authorization: Basic <base64(shop_id:secret_key)>
        Idempotence-Key: <unique_key>

        Body:
        {
            "amount": {
                "value": "1999.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://your-site.com/payment/success"
            },
            "capture": true,
            "description": "Заказ #123",
            "metadata": {
                "order_id": 123,
                "user_id": 456
            }
        }

        Документация:
        https://yookassa.ru/developers/api#create_payment
        """

        # Генерировать уникальный ключ идемпотентности
        idempotence_key = str(uuid.uuid4())

        # TODO: Отправить HTTP запрос к API ЮKassa
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     auth = aiohttp.BasicAuth(self.shop_id, self.secret_key)
        #     headers = {
        #         "Idempotence-Key": idempotence_key,
        #         "Content-Type": "application/json"
        #     }
        #     data = {
        #         "amount": {
        #             "value": str(amount),
        #             "currency": currency
        #         },
        #         "confirmation": {
        #             "type": "redirect",
        #             "return_url": f"https://your-site.com/payment/success?order_id={order_id}"
        #         },
        #         "capture": True,
        #         "description": description,
        #         "metadata": {
        #             "order_id": order_id,
        #             "user_id": user_id
        #         }
        #     }
        #     async with session.post(
        #         f"{self.api_url}/payments",
        #         auth=auth,
        #         headers=headers,
        #         json=data
        #     ) as response:
        #         result = await response.json()
        #         return {
        #             "payment_id": result["id"],
        #             "payment_url": result["confirmation"]["confirmation_url"],
        #             "status": result["status"]
        #         }

        return {
            "payment_id": f"yookassa_{order_id}",
            "payment_url": "https://yookassa.ru/checkout/...",
            "status": "pending"
        }

    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа

        TODO: Реализовать через GET запрос
        GET https://api.yookassa.ru/v3/payments/{payment_id}
        """
        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": Decimal(0)
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменить платеж

        TODO: Реализовать через POST запрос
        POST https://api.yookassa.ru/v3/payments/{payment_id}/cancel
        """
        return False

    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Вернуть деньги

        TODO: Реализовать через POST запрос
        POST https://api.yookassa.ru/v3/refunds
        """
        return {
            "refund_id": f"refund_{payment_id}",
            "status": "pending",
            "amount": amount or Decimal(0)
        }
