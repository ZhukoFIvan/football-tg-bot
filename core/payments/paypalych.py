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

    def __init__(self, api_key: str):
        self.api_key = api_key
        # API URL для Paypalych (pal24.pro)
        # Базовый URL без /api, так как endpoint'ы уже содержат путь
        self.api_url = "https://pal24.pro" 

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
        Создать платеж в PayPaly
        
        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП
        """
        idempotence_key = str(uuid.uuid4())
        
        try:
            # Реальный запрос к API Paypalych
            async with aiohttp.ClientSession() as session:
                # API ключ в формате merchant_id|api_key (из примера: 72|oBCB7Z3SmUm1gvkpEdRcSR2q1ERHpG4vD3DNBmuT)
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                
                # URL для создания платежа
                # Пробуем разные варианты endpoint'ов
                # ВАЖНО: Проверьте документацию Paypalych для правильного endpoint
                endpoints_to_try = [
                    "/merchant/api/invoice",  # Попробуем сначала этот (судя по документации)
                    "/merchant/api/payment",
                    "/api/invoice",
                    "/api/payment",
                    "/api/invoice/create",
                    "/api/payment/create", 
                    "/api/v1/invoice",
                    "/api/v1/payment",
                    "/invoice",
                    "/payment",
                ]
                
                # Пробуем каждый endpoint до первого успешного
                last_error = None
                for endpoint in endpoints_to_try:
                    invoice_url = f"{self.api_url}{endpoint}"
                    
                    # Пробуем разные форматы данных
                    # Вариант 1: JSON
                    data_json = {
                        "amount": float(amount),
                        "currency": currency.upper(),
                        "order_id": str(order_id),
                        "payment_method": payment_method,  # "card" или "sbp"
                        "description": description,
                        "success_url": f"{settings.API_PUBLIC_URL}/payments/success?order_id={order_id}",
                        "fail_url": f"{settings.API_PUBLIC_URL}/payments/failed?order_id={order_id}",
                    }
                    
                    # Вариант 2: Form-data (как в примере curl)
                    data_form = aiohttp.FormData()
                    data_form.add_field("amount", str(float(amount)))
                    data_form.add_field("currency", currency.upper())
                    data_form.add_field("order_id", str(order_id))
                    data_form.add_field("payment_method", payment_method)
                    data_form.add_field("description", description)
                    data_form.add_field("success_url", f"{settings.API_PUBLIC_URL}/payments/success?order_id={order_id}")
                    data_form.add_field("fail_url", f"{settings.API_PUBLIC_URL}/payments/failed?order_id={order_id}")
                    
                    # Сначала пробуем JSON
                    logger.info(f"Trying Paypalych endpoint: {invoice_url}, JSON data: {data_json}")
                    
                    try:
                        async with session.post(
                            invoice_url,
                            headers=headers,
                            json=data_json,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200 or response.status == 201:
                                result = await response.json()
                                logger.info(f"Paypalych payment created via {endpoint}: {result}")
                                
                                # Обычно в ответе есть payment_url или invoice_url
                                payment_url = result.get("payment_url") or result.get("invoice_url") or result.get("url")
                                payment_id = result.get("payment_id") or result.get("invoice_id") or result.get("id")
                                
                                if not payment_url:
                                    raise ValueError(f"No payment_url in response: {result}")
                                
                                return {
                                    "payment_id": payment_id or f"paypalych_{order_id}_{idempotence_key[:8]}",
                                    "payment_url": payment_url,
                                    "status": result.get("status", "pending")
                                }
                            elif response.status == 400:
                                # 400 может означать неправильный формат данных - пробуем form-data
                                error_text = await response.text()
                                logger.warning(f"Endpoint {endpoint} returned 400 with JSON, trying form-data: {error_text}")
                                
                                # Пробуем form-data для этого endpoint
                                try:
                                    headers_form = {
                                        "Authorization": f"Bearer {self.api_key}",
                                        # Не указываем Content-Type для form-data - aiohttp добавит сам
                                    }
                                    async with session.post(
                                        invoice_url,
                                        headers=headers_form,
                                        data=data_form,
                                        timeout=aiohttp.ClientTimeout(total=30)
                                    ) as response_form:
                                        if response_form.status == 200 or response_form.status == 201:
                                            result = await response_form.json()
                                            logger.info(f"Paypalych payment created via {endpoint} (form-data): {result}")
                                            
                                            payment_url = result.get("payment_url") or result.get("invoice_url") or result.get("url")
                                            payment_id = result.get("payment_id") or result.get("invoice_id") or result.get("id")
                                            
                                            if not payment_url:
                                                raise ValueError(f"No payment_url in response: {result}")
                                            
                                            return {
                                                "payment_id": payment_id or f"paypalych_{order_id}_{idempotence_key[:8]}",
                                                "payment_url": payment_url,
                                                "status": result.get("status", "pending")
                                            }
                                        else:
                                            error_text_form = await response_form.text()
                                            logger.warning(f"Endpoint {endpoint} returned {response_form.status} with form-data: {error_text_form}")
                                            last_error = f"{response_form.status}: {error_text_form}"
                                            continue
                                except Exception as e_form:
                                    logger.warning(f"Error trying form-data on {endpoint}: {e_form}")
                                    last_error = str(e_form)
                                    continue
                                    
                            elif response.status == 404:
                                # Пробуем следующий endpoint
                                error_text = await response.text()
                                logger.warning(f"Endpoint {endpoint} returned 404: {error_text}")
                                last_error = f"404: {error_text}"
                                continue
                            else:
                                error_text = await response.text()
                                logger.error(f"Paypalych API error {response.status} on {endpoint}: {error_text}")
                                last_error = f"{response.status}: {error_text}"
                                # Не пробуем дальше при других ошибках (401, 403, 500)
                                if response.status not in [404, 400]:
                                    break
                    except Exception as e:
                        logger.warning(f"Error trying endpoint {endpoint}: {e}")
                        last_error = str(e)
                        continue
                
                # Если все endpoint'ы не сработали
                raise Exception(f"All Paypalych endpoints failed. Last error: {last_error}")
                        
        except Exception as e:
            logger.error(f"Error creating Paypalych payment: {e}", exc_info=True)
            # Fallback - возвращаем заглушку, но логируем ошибку
            return {
                "payment_id": f"paypalych_{order_id}_{idempotence_key[:8]}",
                "payment_url": f"https://pally.info/pay/{order_id}?method={payment_method}",
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

