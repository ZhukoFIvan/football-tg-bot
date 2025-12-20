"""
Модуль платежей
"""
from core.payments.base import PaymentProvider
from core.payments.telegram_stars import TelegramStarsProvider
from core.payments.yookassa import YookassaProvider

__all__ = [
    "PaymentProvider",
    "TelegramStarsProvider",
    "YookassaProvider",
]
