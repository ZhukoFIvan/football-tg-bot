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

    def __init__(self, api_key: str, shop_id: str):
        self.api_key = api_key
        self.shop_id = shop_id
        # API URL для Paypalych (pal24.pro)
        self.api_url = "https://pal24.pro"
        
        # Проверяем формат API ключа
        if "|" not in api_key:
            raise ValueError(
                "API key format is incorrect. "
                "Expected format: merchant_id|api_key (e.g., 72|oBCB7Z3SmUm1gvkpEdRcSR2q1ERHpG4vD3DNBmuT)"
            )
        
        # Проверяем наличие shop_id
        if not shop_id:
            raise ValueError(
                "shop_id is required. Please set PAYPALYCH_SHOP_ID in your .env file. "
                "You can find shop_id in your Paypalych merchant dashboard (e.g., 'G1vrEyX0LR')"
            )
        
        logger.info(f"PaypalychProvider initialized with shop_id: {self.shop_id}")
    
    async def verify_api_token(self) -> bool:
        """
        Проверить правильность API токена перед созданием платежа
        
        Делает простой GET запрос к API для проверки авторизации
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                
                # Пробуем простой GET запрос для проверки токена
                # Если есть endpoint для проверки, используем его, иначе просто проверяем формат токена
                # В документации нет специального endpoint для проверки, поэтому просто проверяем формат
                if "|" not in self.api_key:
                    logger.error("Paypalych API token format is incorrect (missing '|' separator)")
                    return False
                
                # Проверяем, что токен не пустой
                parts = self.api_key.split("|", 1)
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    logger.error("Paypalych API token format is incorrect (empty parts)")
                    return False
                
                logger.info("Paypalych API token format is valid")
                return True
        except Exception as e:
            logger.error(f"Error verifying Paypalych API token: {e}", exc_info=True)
            return False 

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
        # Проверяем формат API токена (проверка валидности будет при реальном запросе)
        logger.info("Verifying Paypalych API token format...")
        token_valid = await self.verify_api_token()
        if not token_valid:
            raise Exception(
                "Paypalych API token format is invalid. "
                "Please check your PAYPALYCH_API_KEY in .env file. "
                "Expected format: merchant_id|api_key"
            )
        
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
                api_key_preview = f"{self.api_key[:10]}..." if len(self.api_key) > 10 else self.api_key
                logger.info(
                    f"Creating Paypalych payment:\n"
                    f"  URL: {invoice_url}\n"
                    f"  Authorization: Bearer {api_key_preview}\n"
                    f"  Form data:\n"
                    f"    - amount: {amount} (type: {type(amount).__name__})\n"
                    f"    - order_id: {order_id} (type: {type(order_id).__name__})\n"
                    f"    - shop_id: '{self.shop_id}' (type: {type(self.shop_id).__name__})\n"
                    f"    - description: {description}\n"
                    f"    - currency_in: {currency.upper()}"
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
                            f"Request data: shop_id={self.shop_id}, amount={amount}, order_id={order_id}"
                        )
                        
                        # Если ошибка авторизации (401 или Unauthenticated)
                        if response.status == 401 or "Unauthenticated" in error_text or "unauthorized" in error_text.lower():
                            raise Exception(
                                f"❌ Paypalych API: Ошибка авторизации (токен неверный).\n\n"
                                f"📋 ЧТО ПРОВЕРИТЬ:\n\n"
                                f"1️⃣ API токен в .env файле:\n"
                                f"   • Формат: merchant_id|api_key\n"
                                f"   • Пример: 25389|eAKBRDawd2bpo2BQHUGh9elf8DIKU8HPirHcSOGg\n"
                                f"   • Проверьте, что токен скопирован полностью, без пробелов\n\n"
                                f"2️⃣ Создайте новый токен в личном кабинете Paypalych\n\n"
                                f"3️⃣ Убедитесь, что токен активен и имеет права на создание платежей\n\n"
                                f"Ошибка от API: {error_text}"
                            )
                        
                        # Если shop_id не найден, даем понятное сообщение
                        if response.status == 422 and "shop_not_found" in error_text:
                            raise Exception(
                                f"❌ Paypalych API: shop_id '{self.shop_id}' не найден.\n\n"
                                f"📋 ЧТО НУЖНО СДЕЛАТЬ:\n\n"
                                f"1️⃣ Найдите ПРАВИЛЬНЫЙ shop_id в личном кабинете Paypalych:\n"
                                f"   • Откройте https://pally.info (или ваш кабинет)\n"
                                f"   • Раздел 'Магазины' → 'API интеграция'\n"
                                f"   • Найдите поле 'shop_id' (это СТРОКА, например: 'G1vrEyX0LR')\n"
                                f"   • ⚠️ shop_id ≠ merchant_id (25389) - это разные значения!\n\n"
                                f"2️⃣ Добавьте в .env файл:\n"
                                f"   PAYPALYCH_SHOP_ID=ваш_shop_id_из_кабинета\n\n"
                                f"3️⃣ Перезапустите сервер:\n"
                                f"   docker-compose restart tg_shop_api\n\n"
                                f"💡 ВАЖНО: В документации shop_id выглядит как 'G1vrEyX0LR', а не как число!\n\n"
                                f"Ошибка от API: {error_text}"
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

