"""
Базовый класс для платежных провайдеров
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict
from decimal import Decimal


class PaymentProvider(ABC):
    """Абстрактный класс для платежных провайдеров"""

    @abstractmethod
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
        Создать платеж

        Args:
            payment_method: "card" для оплаты картой, "sbp" для СБП
            user_email: Email пользователя (опционально)
            user_ip: IP адрес пользователя (опционально)

        Returns:
            {
                "payment_id": str,
                "payment_url": str,  # Ссылка для оплаты
                "status": str
            }
        """
        pass

    @abstractmethod
    async def check_payment(self, payment_id: str) -> Dict:
        """
        Проверить статус платежа

        Returns:
            {
                "payment_id": str,
                "status": str,  # pending, success, failed, cancelled
                "amount": Decimal,
                "paid_at": datetime (optional)
            }
        """
        pass

    @abstractmethod
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменить платеж

        Returns:
            True если успешно отменен
        """
        pass

    @abstractmethod
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Вернуть деньги

        Args:
            payment_id: ID платежа
            amount: Сумма возврата (None = полный возврат)

        Returns:
            {
                "refund_id": str,
                "status": str,
                "amount": Decimal
            }
        """
        pass
