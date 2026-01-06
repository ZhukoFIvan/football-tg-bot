"""
Оплата через FreeKassa
https://www.freekassa.ru/
"""
from typing import Dict, Optional
from decimal import Decimal
import uuid
import hashlib
import urllib.parse

from core.payments.base import PaymentProvider


class FreeKassaProvider(PaymentProvider):
    """Провайдер оплаты через FreeKassa"""

    def __init__(self, merchant_id: str, secret_key: str, secret_key2: str):
        self.merchant_id = merchant_id
        self.secret_key = secret_key  # Secret Key 1
        self.secret_key2 = secret_key2  # Secret Key 2
        self.api_url = "https://pay.freekassa.ru/"

    def _generate_signature(self, amount: Decimal, order_id: int, currency: str = "RUB") -> str:
        """
        Генерация подписи для FreeKassa
        
        Формула: md5(merchant_id:amount:secret_key:order_id)
        """
        amount_str = f"{amount:.2f}"
        sign_string = f"{self.merchant_id}:{amount_str}:{self.secret_key}:{order_id}"
        return hashlib.md5(sign_string.encode()).hexdigest()

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int,
        payment_method: str = "card"  # "card" для карты, "sbp" для СБП
    ) -> Dict:
        """
        Создать платеж в FreeKassa
        
        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП
        """
        # Генерируем подпись
        signature = self._generate_signature(amount, order_id, currency)
        
        # Определяем способ оплаты для FreeKassa
        # FreeKassa использует параметр i для выбора способа оплаты
        # i=1 - банковские карты (Visa, MasterCard, МИР)
        # i=10 - СБП (Система быстрых платежей)
        # Если не указать i, пользователь сможет выбрать способ оплаты на странице FreeKassa
        payment_method_code = None
        if payment_method == "card":
            payment_method_code = "1"  # Банковские карты
        elif payment_method == "sbp":
            payment_method_code = "10"  # СБП
        
        # Формируем URL для оплаты
        # Параметры согласно документации FreeKassa:
        # m - MERCHANT_ID (ID магазина)
        # oa - сумма платежа
        # o - MERCHANT_ORDER_ID (номер заказа)
        # s - подпись (md5(merchant_id:amount:secret_key:order_id))
        # currency - валюта (RUB)
        # i - способ оплаты (опционально)
        params = {
            "m": self.merchant_id,
            "oa": f"{amount:.2f}",
            "o": str(order_id),
            "s": signature,
            "currency": currency,
            "us_user_id": str(user_id),
            "us_description": description[:255]  # Ограничение длины
        }
        
        # Добавить способ оплаты, если указан
        if payment_method_code:
            params["i"] = payment_method_code
        
        payment_url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
        
        return {
            "payment_id": f"freekassa_{order_id}_{uuid.uuid4().hex[:8]}",
            "payment_url": payment_url,
            "status": "pending"
        }

    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа через API FreeKassa
        
        FreeKassa отправляет уведомления на указанный URL (webhook),
        но можно также проверить статус через API
        """
        # TODO: Реализовать проверку статуса через API FreeKassa
        # Обычно FreeKassa отправляет уведомления на указанный URL
        # Для проверки статуса можно использовать:
        # GET https://www.freekassa.ru/api.php?merchant_id=...&s=...&action=get_order_status&order_id=...
        
        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": Decimal(0)
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменить платеж
        
        В FreeKassa отмена обычно не поддерживается напрямую,
        но можно обработать через webhook при отмене пользователем
        """
        return False

    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Вернуть деньги
        
        TODO: Реализовать возврат через API FreeKassa
        Обычно возвраты обрабатываются через личный кабинет или API
        """
        return {
            "refund_id": f"refund_{payment_id}",
            "status": "pending",
            "amount": amount or Decimal(0)
        }

    def verify_webhook_signature(self, amount: Decimal, order_id: int, signature: str) -> bool:
        """
        Проверить подпись webhook от FreeKassa
        
        Формула для проверки: md5(merchant_id:amount:secret_key2:order_id)
        """
        amount_str = f"{amount:.2f}"
        sign_string = f"{self.merchant_id}:{amount_str}:{self.secret_key2}:{order_id}"
        expected_signature = hashlib.md5(sign_string.encode()).hexdigest()
        return signature.lower() == expected_signature.lower()

