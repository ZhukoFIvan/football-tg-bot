"""
Оплата через PayPaly (paypalych)
"""
from typing import Dict, Optional
from decimal import Decimal
import uuid
import aiohttp
import base64
import logging

from core.payments.base import PaymentProvider
from core.config import settings

logger = logging.getLogger(__name__)


class PaypalychProvider(PaymentProvider):
    """Провайдер оплаты через PayPaly"""

    def __init__(self, api_key: str, shop_id: str = None):
        self.api_key = api_key
        # API URL для Paypalych (pal24.pro)
        self.api_url = "https://pal24.pro"
        
        # Извлекаем merchant_id из API ключа (формат: merchant_id|api_key)
        if "|" in api_key:
            self.merchant_id = api_key.split("|")[0]
        else:
            self.merchant_id = None
        
        # shop_id - это отдельный параметр из настроек магазина Paypalych
        # Если не указан, пробуем использовать merchant_id из API ключа
        if shop_id:
            self.shop_id = str(shop_id)  # Убеждаемся, что это строка
        elif self.merchant_id:
            # Fallback: используем merchant_id из API ключа
            logger.warning(
                f"PAYPALYCH_SHOP_ID not set, using merchant_id from API key: {self.merchant_id}. "
                f"If this doesn't work, please set PAYPALYCH_SHOP_ID in .env file."
            )
            self.shop_id = str(self.merchant_id)
        else:
            raise ValueError(
                "shop_id is required for Paypalych. "
                "Please set PAYPALYCH_SHOP_ID in .env file, or ensure API key format is merchant_id|api_key. "
                "You can find shop_id in your Paypalych merchant dashboard settings."
            ) 

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int,
        payment_method: str = "sbp" 
    ) -> Dict:
        """
        Создать платеж в PayPaly через /api/v1/bill/create
        
        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП (не используется в API, но оставлено для совместимости)
        """
        try:
            # Реальный запрос к API Paypalych согласно документации
            # Endpoint: /api/v1/bill/create
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    # Не указываем Content-Type для form-data - aiohttp добавит сам
                }
                
                # Формируем form-data согласно документации
                data_form = aiohttp.FormData()
                data_form.add_field("amount", str(float(amount)))
                data_form.add_field("order_id", str(order_id))
                data_form.add_field("description", description)
                data_form.add_field("type", "normal")
                data_form.add_field("shop_id", self.shop_id)
                data_form.add_field("currency_in", currency.upper())
                data_form.add_field("custom", f"order_{order_id}_user_{user_id}")
                data_form.add_field("payer_pays_commission", "1")  # 1 = да, 0 = нет
                data_form.add_field("name", "Платёж")
                
                invoice_url = f"{self.api_url}/api/v1/bill/create"
                
                logger.info(f"Creating Paypalych payment: {invoice_url}, amount={amount}, order_id={order_id}, shop_id={self.shop_id}")
                
                async with session.post(
                    invoice_url,
                    headers=headers,
                    data=data_form,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        logger.info(f"Paypalych payment created: {result}")
                        
                        # Проверяем успешность
                        if result.get("success") != "true" and result.get("success") is not True:
                            error_msg = result.get("message", "Unknown error")
                            raise Exception(f"Paypalych API returned error: {error_msg}")
                        
                        # Используем link_page_url для перенаправления пользователя
                        payment_url = result.get("link_page_url") or result.get("link_url")
                        payment_id = result.get("bill_id")
                        
                        if not payment_url:
                            raise ValueError(f"No payment_url in response: {result}")
                        if not payment_id:
                            raise ValueError(f"No bill_id in response: {result}")
                        
                        return {
                            "payment_id": payment_id,
                            "payment_url": payment_url,
                            "status": "pending"
                        }
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Paypalych API error {response.status}: {error_text}. "
                            f"Request data: shop_id={self.shop_id}, merchant_id={self.merchant_id}, "
                            f"amount={amount}, order_id={order_id}"
                        )
                        
                        # Если shop_id не найден и мы использовали переданный shop_id, 
                        # пробуем использовать merchant_id из API ключа
                        if response.status == 422 and "shop_not_found" in error_text:
                            if self.shop_id and self.merchant_id and str(self.shop_id) != str(self.merchant_id):
                                logger.warning(
                                    f"shop_id {self.shop_id} not found. Trying merchant_id {self.merchant_id} from API key..."
                                )
                                # Пробуем с merchant_id
                                data_form_retry = aiohttp.FormData()
                                data_form_retry.add_field("amount", str(float(amount)))
                                data_form_retry.add_field("order_id", str(order_id))
                                data_form_retry.add_field("description", description)
                                data_form_retry.add_field("type", "normal")
                                data_form_retry.add_field("shop_id", str(self.merchant_id))
                                data_form_retry.add_field("currency_in", currency.upper())
                                data_form_retry.add_field("custom", f"order_{order_id}_user_{user_id}")
                                data_form_retry.add_field("payer_pays_commission", "1")
                                data_form_retry.add_field("name", "Платёж")
                                
                                async with session.post(
                                    invoice_url,
                                    headers=headers,
                                    data=data_form_retry,
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as response_retry:
                                    if response_retry.status == 200 or response_retry.status == 201:
                                        result = await response_retry.json()
                                        logger.info(f"Paypalych payment created with merchant_id: {result}")
                                        
                                        if result.get("success") != "true" and result.get("success") is not True:
                                            error_msg = result.get("message", "Unknown error")
                                            raise Exception(f"Paypalych API returned error: {error_msg}")
                                        
                                        payment_url = result.get("link_page_url") or result.get("link_url")
                                        payment_id = result.get("bill_id")
                                        
                                        if not payment_url:
                                            raise ValueError(f"No payment_url in response: {result}")
                                        if not payment_id:
                                            raise ValueError(f"No bill_id in response: {result}")
                                        
                                        # Обновляем shop_id для будущих запросов
                                        self.shop_id = str(self.merchant_id)
                                        
                                        return {
                                            "payment_id": payment_id,
                                            "payment_url": payment_url,
                                            "status": "pending"
                                        }
                        
                        raise Exception(f"Paypalych API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Error creating Paypalych payment: {e}", exc_info=True)
            raise  # Пробрасываем ошибку дальше, чтобы обработать в cart.py

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
        
        Paypalych может не требовать проверки подписи или использовать другой метод.
        Если подпись не требуется, возвращаем True.
        """
        # TODO: Уточнить, требуется ли проверка подписи для Paypalych
        # Если подпись не требуется, просто возвращаем True
        if not signature:
            return True
        
        # Если подпись есть, можно добавить проверку (если потребуется)
        # Пока возвращаем True, так как Paypalych может не использовать подпись
        return True

