"""
Оплата через FreeKassa через API
https://docs.freekassa.net/
"""
from typing import Dict, Optional
from decimal import Decimal
import uuid
import hashlib
import hmac
import logging
import time
import aiohttp
import json
import urllib.parse

from core.payments.base import PaymentProvider
from core.config import settings

logger = logging.getLogger(__name__)


class FreeKassaProvider(PaymentProvider):
    """Провайдер оплаты через FreeKassa (API)"""

    def __init__(self, merchant_id: str, api_key: str, secret_key2: str):
        self.merchant_id = merchant_id  # Shop ID
        self.api_key = api_key  # API ключ из личного кабинета
        self.secret_key2 = secret_key2  # Secret Key 2 для проверки webhook
        self.api_url = "https://api.fk.life/v1"
        
        # Проверяем наличие обязательных параметров
        if not merchant_id:
            raise ValueError(
                "merchant_id is required. Please set FREEKASSA_MERCHANT_ID in your .env file. "
                "You can find merchant_id (shopId) in your FreeKassa merchant dashboard"
            )
        if not api_key:
            raise ValueError(
                "api_key is required. Please set FREEKASSA_API_KEY in your .env file. "
                "You can find API key in your FreeKassa dashboard settings"
            )
        if not secret_key2:
            raise ValueError(
                "secret_key2 is required. Please set FREEKASSA_SECRET_KEY2 in your .env file. "
                "This is Secret Key 2 from your FreeKassa dashboard (used for webhook verification)"
            )
        
        logger.info(f"FreeKassaProvider initialized with merchant_id: {self.merchant_id}")

    def _generate_api_signature(self, request_body: dict, api_key: str) -> str:
        """
        Генерация подписи для API запросов FreeKassa
        
        Согласно документации API v1 (раздел 2.2. Подпись запросов):
        1. Берем все ключи тела запроса (кроме signature)
        2. Сортируем их в алфавитном порядке
        3. Берем их значения и преобразуем в строки
        4. Соединяем значения через символ |
        5. Используем HMAC SHA256 с API_KEY как ключом для HMAC
        
        ВАЖНО: 
        - signature НЕ должен быть в request_body при генерации подписи!
        - Все значения должны быть преобразованы в строки
        - Числа должны быть без лишних нулей (например, 10.0 -> "10" или "10.0" в зависимости от типа)
        """
        # Создаем копию тела запроса без signature и None значений
        # Согласно документации, None значения не должны участвовать в подписи
        body_for_signature = {
            k: v for k, v in request_body.items() 
            if k != "signature" and v is not None
        }
        
        # Сортируем ключи в алфавитном порядке
        sorted_keys = sorted(body_for_signature.keys())
        
        # Берем значения в отсортированном порядке и преобразуем в строки
        # Важно: сохраняем оригинальный формат чисел (10.0 -> "10.0", не "10")
        values = []
        for key in sorted_keys:
            value = body_for_signature[key]
            # Преобразуем в строку с учетом типа
            if isinstance(value, (float, int)):
                # Для чисел сохраняем оригинальный формат (10.0 остается "10.0")
                values.append(str(value))
            else:
                values.append(str(value))
        
        sign_string = "|".join(values)
        
        # Генерируем HMAC SHA256 с API ключом как ключом для HMAC
        signature = hmac.new(
            api_key.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Подробное логирование для отладки
        logger.info(f"🔐 Generating FreeKassa API signature:")
        logger.info(f"   Sorted keys: {sorted_keys}")
        logger.info(f"   Sign string (full): {sign_string}")
        logger.info(f"   API key length: {len(api_key)} chars")
        logger.info(f"   Signature: {signature}")
        
        return signature

    async def verify_api_token(self) -> bool:
        """
        Проверить правильность настроек FreeKassa перед созданием платежа
        
        Проверяет формат и наличие всех необходимых параметров
        """
        try:
            # Проверяем, что все параметры заполнены
            if not self.merchant_id or not self.api_key or not self.secret_key2:
                logger.error("FreeKassa configuration is incomplete")
                return False
            
            # Проверяем формат merchant_id (обычно это число)
            try:
                int(self.merchant_id)
            except ValueError:
                logger.warning(f"FreeKassa merchant_id should be numeric, got: {self.merchant_id}")
            
            logger.info("FreeKassa configuration is valid")
            return True
        except Exception as e:
            logger.error(f"Error verifying FreeKassa configuration: {e}", exc_info=True)
            return False

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        user_id: int,
        payment_method: str = "card",  # "card" для карты, "sbp" для СБП
        user_email: Optional[str] = None,
        user_ip: Optional[str] = None
    ) -> Dict:
        """
        Создать платеж в FreeKassa через API
        
        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП
            user_email: Email пользователя (если не указан, используется tgid@telegram.org)
            user_ip: IP адрес пользователя (если не указан, используется IP сервера)
        """
        # Проверяем настройки перед созданием платежа
        logger.info("Verifying FreeKassa configuration...")
        config_valid = await self.verify_api_token()
        if not config_valid:
            raise Exception(
                "FreeKassa configuration is invalid. "
                "Please check your FREEKASSA_MERCHANT_ID, FREEKASSA_API_KEY and FREEKASSA_SECRET_KEY2 in .env file."
            )
        
        try:
            # Проверяем минимальную сумму (обычно для FreeKassa минимум 1-10 RUB)
            if amount < 1:
                raise ValueError(
                    f"Минимальная сумма платежа для FreeKassa — 1 RUB. "
                    f"Текущая сумма: {amount} RUB."
                )
            
            # Определяем способ оплаты для FreeKassa API
            # i=36 - банковские карты РФ
            # i=44 - СБП (QR код)
            # i=43 - SberPay
            payment_method_code = None
            payment_method_name = "любой способ"
            if payment_method == "card":
                payment_method_code = 36  # Банковские карты РФ
                payment_method_name = "банковская карта"
            elif payment_method == "sbp":
                payment_method_code = 44  # СБП (QR код)
                payment_method_name = "СБП"
            
            # Генерируем nonce (уникальный ID запроса, должен быть больше предыдущего)
            # Используем timestamp в миллисекундах для уникальности
            nonce = int(time.time() * 1000)
            
            # Убеждаемся, что merchant_id - это число
            try:
                shop_id_int = int(self.merchant_id)
                shop_id_for_signature = str(shop_id_int)
            except ValueError:
                raise ValueError(f"FREEKASSA_MERCHANT_ID must be a number, got: {self.merchant_id}")
            
            # Формируем email (реальный email или tgid@telegram.org)
            email = user_email if user_email else f"{user_id}@telegram.org"
            
            # Формируем IP (IP клиента или сервера, можно передать IP сервера)
            ip = user_ip if user_ip else "127.0.0.1"  # В реальности нужно получить IP клиента
            
            # ВАЖНО: result_url - URL для webhook уведомлений от FreeKassa
            result_url = f"{settings.API_PUBLIC_URL}/api/payments/webhook/freekassa"
            # Получаем username бота из настроек (без хардкода!)
            bot_username = getattr(settings, 'BOT_USERNAME', '').strip()
            if not bot_username:
                raise ValueError(
                    "BOT_USERNAME не установлен в .env файле. "
                    "Установите BOT_USERNAME=ваш_бот_username (например: Romlx_store_bot или Romix_store_bot)"
                )
            # Frontend страницы результатов (не API, а Next.js)
            success_url = f"{settings.FRONTEND_URL}/payments/success?order_id={order_id}&bot_username={bot_username}"
            fail_url = f"{settings.FRONTEND_URL}/payments/failed?order_id={order_id}&bot_username={bot_username}"
            
            # Формируем данные для API запроса
            # Согласно документации: POST https://api.fk.life/v1/orders/create
            api_endpoint = f"{self.api_url}/orders/create"
            
            # Тело запроса БЕЗ signature (signature добавим после генерации)
            # Согласно документации API, shopId, nonce должны быть в теле запроса
            # Важно: amount должен быть числом (float), не строкой
            request_body = {
                "shopId": shop_id_int,  # ID магазина (обязательно в теле запроса!)
                "nonce": nonce,  # Уникальный ID запроса (обязательно в теле запроса!)
                "paymentId": str(order_id),  # Номер заказа в нашем магазине
                "i": payment_method_code,  # Способ оплаты
                "email": email,  # Email клиента
                "ip": ip,  # IP адрес клиента
                "amount": float(amount),  # Сумма платежа (число, не строка!)
                "currency": currency.upper(),  # Валюта
                "result_url": result_url,  # URL для webhook уведомлений
                "success_url": success_url,  # URL для успешной оплаты
                "fail_url": fail_url  # URL для неудачной оплаты
            }
            
            # Логируем тело запроса для отладки (перед генерацией подписи)
            logger.debug(f"Request body before signature: {json.dumps(request_body, ensure_ascii=False, indent=2)}")
            
            # Генерируем подпись из тела запроса (БЕЗ signature!)
            signature = self._generate_api_signature(request_body, self.api_key)
            logger.info(f"Generated signature: {signature[:20]}... (shopId={shop_id_int}, nonce={nonce})")
            
            # Теперь добавляем signature в тело запроса
            request_body["signature"] = signature
            
            # Параметры запроса (query parameters) - для совместимости
            query_params = {
                "shopId": shop_id_for_signature,
                "nonce": str(nonce),
                "signature": signature
            }
            
            logger.info(f"Query params: shopId={query_params['shopId']}, nonce={query_params['nonce']}, signature={query_params['signature'][:20]}...")
            
            # Логируем все параметры для отладки (без секретных ключей)
            logger.info(
                f"Creating FreeKassa payment via API:\n"
                f"  Endpoint: {api_endpoint}\n"
                f"  Shop ID: {self.merchant_id}\n"
                f"  Nonce: {nonce}\n"
                f"  Amount: {amount} {currency.upper()}\n"
                f"  Order ID: {order_id}\n"
                f"  Payment method: {payment_method_name} (code: {payment_method_code})\n"
                f"  Email: {email}\n"
                f"  IP: {ip}\n"
                f"  Description: {description[:50]}...\n"
                f"  Result URL (webhook): {result_url}\n"
                f"  Success URL: {success_url}\n"
                f"  Fail URL: {fail_url}"
            )
            
            # Отправляем запрос к API FreeKassa
            async with aiohttp.ClientSession() as session:
                # Формируем полный URL с query параметрами
                query_string = urllib.parse.urlencode(query_params)
                url_with_params = f"{api_endpoint}?{query_string}"
                
                logger.info(f"Request URL: {url_with_params}")
                logger.info(f"Request body: {json.dumps(request_body, ensure_ascii=False)}")
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    url_with_params,
                    json=request_body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200 or response.status == 201:
                        # Проверяем заголовок Location для получения ссылки на оплату
                        location = response.headers.get("Location")
                        
                        if location:
                            logger.info(f"FreeKassa payment created successfully. Location: {location}")
                            
                            # Также можно получить JSON ответ, если есть
                            try:
                                result = await response.json()
                                logger.info(f"FreeKassa API response: {result}")
                                
                                # Если в ответе есть payment_id или order_id, используем его
                                payment_id_from_api = result.get("id") or result.get("orderId") or result.get("paymentId")
                                if payment_id_from_api:
                                    payment_id = f"freekassa_{payment_id_from_api}"
                                else:
                                    payment_id = f"freekassa_{order_id}_{uuid.uuid4().hex[:8]}"
                            except:
                                payment_id = f"freekassa_{order_id}_{uuid.uuid4().hex[:8]}"
                            
                            return {
                                "payment_id": payment_id,
                                "payment_url": location,
                                "status": "pending"
                            }
                        else:
                            # Если Location нет, пробуем получить из JSON
                            try:
                                result = await response.json()
                                payment_url = result.get("location") or result.get("url") or result.get("payment_url")
                                
                                if payment_url:
                                    payment_id_from_api = result.get("id") or result.get("orderId") or result.get("paymentId")
                                    if payment_id_from_api:
                                        payment_id = f"freekassa_{payment_id_from_api}"
                                    else:
                                        payment_id = f"freekassa_{order_id}_{uuid.uuid4().hex[:8]}"
                                    
                                    return {
                                        "payment_id": payment_id,
                                        "payment_url": payment_url,
                                        "status": "pending"
                                    }
                                else:
                                    raise ValueError(f"No payment URL in response: {result}")
                            except Exception as e:
                                error_text = await response.text()
                                raise Exception(
                                    f"FreeKassa API не вернул ссылку на оплату. "
                                    f"Status: {response.status}, Response: {error_text}"
                                )
                    else:
                        # Пробуем распарсить JSON ошибки
                        error_message = None
                        try:
                            error_json = await response.json()
                            error_message = error_json.get("message") or error_json.get("error") or str(error_json)
                        except:
                            error_text = await response.text()
                            error_message = error_text
                        
                        logger.error(
                            f"FreeKassa API error {response.status}: {error_message}. "
                            f"Request: shopId={self.merchant_id}, amount={amount}, order_id={order_id}"
                        )
                        
                        # Если ошибка авторизации (401)
                        if response.status == 401:
                            raise Exception(
                                f"❌ FreeKassa API: Ошибка авторизации (API ключ неверный).\n\n"
                                f"📋 ЧТО ПРОВЕРИТЬ:\n\n"
                                f"1️⃣ API ключ в .env файле:\n"
                                f"   • Проверьте FREEKASSA_API_KEY в .env файле\n"
                                f"   • Убедитесь, что ключ скопирован полностью, без пробелов\n"
                                f"   • Создайте новый API ключ в личном кабинете FreeKassa\n\n"
                                f"2️⃣ Убедитесь, что API ключ активен и имеет права на создание платежей\n\n"
                                f"Ошибка от API: {error_message}"
                            )
                        
                        raise Exception(f"FreeKassa API error {response.status}: {error_message}")
        
        except ValueError as e:
            # Пробрасываем ValueError как есть (для минимальной суммы)
            raise
        except Exception as e:
            logger.error(f"Error creating FreeKassa payment: {e}", exc_info=True)
            raise

    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа через API FreeKassa
        
        FreeKassa отправляет уведомления на указанный URL (webhook),
        но можно также проверить статус через API
        """
        # TODO: Реализовать проверку статуса через API FreeKassa
        # Можно использовать GET /orders с параметрами orderId или paymentId
        
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
        Можно использовать POST /orders/refund
        """
        return {
            "refund_id": f"refund_{payment_id}",
            "status": "pending",
            "amount": amount or Decimal(0)
        }

    def verify_webhook_signature(self, amount: Decimal, order_id: int, signature: str) -> bool:
        """
        Проверить подпись webhook от FreeKassa
        
        Формула для проверки: md5(MERCHANT_ID:AMOUNT:SECRET_KEY2:MERCHANT_ORDER_ID)
        
        ВАЖНО: Для webhook используется SECRET_KEY2, а не API_KEY!
        """
        if not signature:
            logger.error("FreeKassa webhook signature is missing")
            return False
        
        try:
            amount_str = f"{amount:.2f}"
            sign_string = f"{self.merchant_id}:{amount_str}:{self.secret_key2}:{order_id}"
            expected_signature = hashlib.md5(sign_string.encode()).hexdigest()
            
            is_valid = signature.lower() == expected_signature.lower()
            
            if not is_valid:
                logger.error(
                    f"Invalid FreeKassa webhook signature for order {order_id}:\n"
                    f"  Expected: {expected_signature}\n"
                    f"  Received: {signature}\n"
                    f"  Sign string: {sign_string}"
                )
            else:
                logger.info(f"FreeKassa webhook signature verified for order {order_id}")
            
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying FreeKassa webhook signature: {e}", exc_info=True)
            return False
