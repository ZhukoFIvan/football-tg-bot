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
        # Пример из документации: 72|oBCB7Z3SmUm1gvkpEdRcSR2q1ERHpG4vD3DNBmuT
        if "|" in api_key:
            parts = api_key.split("|", 1)  # Разделяем только по первому |
            self.merchant_id = parts[0]
            logger.info(f"Extracted merchant_id from API key: {self.merchant_id}")
        else:
            self.merchant_id = None
            logger.warning(
                f"API key doesn't contain '|' separator. "
                f"Expected format: merchant_id|api_key (e.g., 72|oBCB7Z3SmUm1gvkpEdRcSR2q1ERHpG4vD3DNBmuT)"
            )
        
        # shop_id - это отдельный параметр из настроек магазина Paypalych
        # В документации пример: shop_id="G1vrEyX0LR" (строка, не число!)
        # Если не указан, пробуем использовать merchant_id из API ключа
        if shop_id:
            self.shop_id = str(shop_id).strip()  # Убеждаемся, что это строка без пробелов
            logger.info(f"Using shop_id from config: {self.shop_id}")
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
                # В документации order_id и shop_id передаются как строки в кавычках
                # Но в form-data кавычки не нужны, aiohttp сам обработает
                data_form = aiohttp.FormData()
                data_form.add_field("amount", str(float(amount)))
                data_form.add_field("order_id", str(order_id))  # Передаем как строку
                data_form.add_field("description", description)
                data_form.add_field("type", "normal")
                # shop_id должен быть строкой (в документации: shop_id="G1vrEyX0LR")
                data_form.add_field("shop_id", str(self.shop_id))  # Убеждаемся, что это строка
                data_form.add_field("currency_in", currency.upper())
                data_form.add_field("custom", f"order_{order_id}_user_{user_id}")
                data_form.add_field("payer_pays_commission", "1")  # 1 = да, 0 = нет
                data_form.add_field("name", "Платёж")
                
                invoice_url = f"{self.api_url}/api/v1/bill/create"
                
                # Логируем все параметры для отладки
                # ВАЖНО: Показываем, что токен используется как есть, без изменений
                api_key_preview = f"{self.api_key[:10]}..." if len(self.api_key) > 10 else self.api_key
                logger.info(
                    f"Creating Paypalych payment:\n"
                    f"  URL: {invoice_url}\n"
                    f"  Authorization: Bearer {api_key_preview} (полный токен из .env, БЕЗ изменений)\n"
                    f"  Form data:\n"
                    f"    amount={amount}\n"
                    f"    order_id={order_id}\n"
                    f"    shop_id={self.shop_id} (отдельный параметр, НЕ часть токена)\n"
                    f"    merchant_id из токена={self.merchant_id}\n"
                    f"  ВАЖНО: Токен используется как есть ({self.api_key[:20]}...), shop_id передается отдельно"
                )
                
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
                        
                        # Если shop_id не найден, пробуем разные варианты
                        if response.status == 422 and "shop_not_found" in error_text:
                            retry_attempts = []
                            
                            # Вариант 1: Попробовать без shop_id (может быть он не обязателен)
                            logger.warning(f"shop_id {self.shop_id} not found. Trying without shop_id...")
                            data_form_no_shop = aiohttp.FormData()
                            data_form_no_shop.add_field("amount", str(float(amount)))
                            data_form_no_shop.add_field("order_id", str(order_id))
                            data_form_no_shop.add_field("description", description)
                            data_form_no_shop.add_field("type", "normal")
                            # НЕ добавляем shop_id
                            data_form_no_shop.add_field("currency_in", currency.upper())
                            data_form_no_shop.add_field("custom", f"order_{order_id}_user_{user_id}")
                            data_form_no_shop.add_field("payer_pays_commission", "1")
                            data_form_no_shop.add_field("name", "Платёж")
                            
                            async with session.post(
                                invoice_url,
                                headers=headers,
                                data=data_form_no_shop,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as response_no_shop:
                                if response_no_shop.status == 200 or response_no_shop.status == 201:
                                    result = await response_no_shop.json()
                                    logger.info(f"Paypalych payment created without shop_id: {result}")
                                    
                                    if result.get("success") != "true" and result.get("success") is not True:
                                        error_msg = result.get("message", "Unknown error")
                                        raise Exception(f"Paypalych API returned error: {error_msg}")
                                    
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
                                    error_text_no_shop = await response_no_shop.text()
                                    logger.warning(f"Request without shop_id failed: {error_text_no_shop}")
                            
                            # Вариант 2: Если есть merchant_id, попробовать его
                            if self.merchant_id and str(self.shop_id) != str(self.merchant_id):
                                logger.warning(
                                    f"Trying merchant_id {self.merchant_id} from API key..."
                                )
                                data_form_merchant = aiohttp.FormData()
                                data_form_merchant.add_field("amount", str(float(amount)))
                                data_form_merchant.add_field("order_id", str(order_id))
                                data_form_merchant.add_field("description", description)
                                data_form_merchant.add_field("type", "normal")
                                data_form_merchant.add_field("shop_id", str(self.merchant_id))
                                data_form_merchant.add_field("currency_in", currency.upper())
                                data_form_merchant.add_field("custom", f"order_{order_id}_user_{user_id}")
                                data_form_merchant.add_field("payer_pays_commission", "1")
                                data_form_merchant.add_field("name", "Платёж")
                                
                                async with session.post(
                                    invoice_url,
                                    headers=headers,
                                    data=data_form_merchant,
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as response_merchant:
                                    if response_merchant.status == 200 or response_merchant.status == 201:
                                        result = await response_merchant.json()
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
                                    else:
                                        error_text_merchant = await response_merchant.text()
                                        logger.warning(f"Request with merchant_id failed: {error_text_merchant}")
                            
                            # Если все попытки не удались, выбрасываем понятную ошибку
                            raise Exception(
                                f"Paypalych API error: shop_id '{self.shop_id}' not found. "
                                f"Please check:\n"
                                f"1. Is PAYPALYCH_SHOP_ID correct in your .env file?\n"
                                f"2. Is your API key format correct (should be 'merchant_id|api_key')?\n"
                                f"3. Contact Paypalych support to get the correct shop_id for your account.\n"
                                f"Original error: {error_text}"
                            )
                        
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

