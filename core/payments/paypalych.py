"""
Оплата через PayPaly (paypalych)
"""
from typing import Dict, Optional
from decimal import Decimal
import uuid
import aiohttp
import base64

from core.payments.base import PaymentProvider


class PaypalychProvider(PaymentProvider):
    """Провайдер оплаты через PayPaly"""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.api_url = "https://paypalych.com/api/v1"  # Примерный URL, нужно уточнить

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int,
        payment_method: str = "card"  # "card" или "sbp"
    ) -> Dict:
        """
        Создать платеж в PayPaly
        
        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП
        """
        idempotence_key = str(uuid.uuid4())
        
        # TODO: Реализовать через HTTP запрос к API PayPaly
        # Примерная структура запроса
        # async with aiohttp.ClientSession() as session:
        #     headers = {
        #         "Authorization": f"Bearer {self.api_key}",
        #         "Content-Type": "application/json",
        #         "X-Idempotency-Key": idempotence_key
        #     }
        #     data = {
        #         "amount": float(amount),
        #         "currency": currency,
        #         "description": description,
        #         "order_id": order_id,
        #         "user_id": user_id,
        #         "payment_method": payment_method,  # "card" или "sbp"
        #         "return_url": f"{settings.API_PUBLIC_URL}/payment/success?order_id={order_id}"
        #     }
        #     async with session.post(
        #         f"{self.api_url}/payments",
        #         headers=headers,
        #         json=data
        #     ) as response:
        #         result = await response.json()
        #         return {
        #             "payment_id": result["payment_id"],
        #             "payment_url": result["payment_url"],
        #             "status": result["status"]
        #         }
        
        return {
            "payment_id": f"paypalych_{order_id}_{idempotence_key[:8]}",
            "payment_url": f"https://paypalych.com/pay/{order_id}?method={payment_method}",
            "status": "pending"
        }

    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа
        """
        # TODO: Реализовать через GET запрос
        # async with aiohttp.ClientSession() as session:
        #     headers = {
        #         "Authorization": f"Bearer {self.api_key}",
        #         "Content-Type": "application/json"
        #     }
        #     async with session.get(
        #         f"{self.api_url}/payments/{payment_id}",
        #         headers=headers
        #     ) as response:
        #         result = await response.json()
        #         return {
        #             "payment_id": payment_id,
        #             "status": result["status"],
        #             "amount": Decimal(result["amount"]),
        #             "paid_at": result.get("paid_at")
        #         }
        
        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": Decimal(0)
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменить платеж
        """
        # TODO: Реализовать через POST запрос
        return False

    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Вернуть деньги
        """
        # TODO: Реализовать через POST запрос
        return {
            "refund_id": f"refund_{payment_id}",
            "status": "pending",
            "amount": amount or Decimal(0)
        }

    def verify_webhook_signature(self, order_id: str, amount: str, signature: str) -> bool:
        """
        Проверить подпись webhook от PayPaly
        
        Формула для проверки зависит от API PayPaly
        Обычно используется: md5(order_id:amount:secret_key) или подобное
        """
        import hashlib
        # TODO: Уточнить формулу проверки подписи для PayPaly
        sign_string = f"{order_id}:{amount}:{self.secret_key}"
        expected_signature = hashlib.md5(sign_string.encode()).hexdigest()
        return signature.lower() == expected_signature.lower()

