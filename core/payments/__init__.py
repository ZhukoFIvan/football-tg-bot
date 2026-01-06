"""
Модуль платежей
"""
from core.payments.base import PaymentProvider
from core.payments.paypalych import PaypalychProvider
from core.payments.freekassa import FreeKassaProvider

__all__ = [
    "PaymentProvider",
    "PaypalychProvider",
    "FreeKassaProvider",
]
