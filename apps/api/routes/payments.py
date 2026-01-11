"""
Webhook эндпоинты для обработки платежных уведомлений
"""
import logging
import re
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from core.db.session import get_db
from core.db.models import Payment, Order, User, OrderItem, BonusTransaction
from core.config import settings
from core.payments.freekassa import FreeKassaProvider
from core.payments.paypalych import PaypalychProvider
from aiogram import Bot
from aiogram.enums import ParseMode

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== PYDANTIC SCHEMAS ====================

class FreeKassaWebhook(BaseModel):
    """Webhook от FreeKassa"""
    MERCHANT_ID: str
    AMOUNT: str
    MERCHANT_ORDER_ID: str
    P_EMAIL: str | None = None
    P_PHONE: str | None = None
    CUR_ID: str | None = None
    SIGN: str
    us_user_id: str | None = None
    us_description: str | None = None


class PaypalychWebhook(BaseModel):
    """Webhook от PayPaly"""
    order_id: str
    amount: str
    status: str
    signature: str | None = None
    user_id: str | None = None


# ==================== HELPER FUNCTIONS ====================

async def send_telegram_notification(
    telegram_id: int,
    message: str,
    bot_token: str = settings.BOT_TOKEN
):
    """
    Отправить уведомление пользователю в Telegram
    
    Args:
        telegram_id: Telegram ID пользователя
        message: Текст сообщения
        bot_token: Токен бота
    """
    try:
        bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
        await bot.send_message(chat_id=telegram_id, text=message)
        await bot.session.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {telegram_id}: {e}")


async def notify_admins_about_purchase(
    user: User,
    order: Order,
    order_items: list,
    payment: Payment = None
):
    """
    Отправить уведомление админам о новой покупке
    
    Args:
        user: Объект пользователя
        order: Объект заказа
        order_items: Список товаров в заказе
        payment: Объект платежа (опционально)
    """
    admin_ids = settings.owner_ids
    if not admin_ids:
        logger.warning("OWNER_TG_IDS не задан - уведомления админам не отправлены")
        return
    
    # Формируем список товаров
    items_text = "\n".join([
        f"  • {item.product_title} x{item.quantity} = {float(item.price * item.quantity):,.2f} ₽"
        for item in order_items
    ])
    
    message = f"""
🎉 <b>Новая покупка!</b>

👤 <b>Пользователь:</b>
   • ID: <code>{user.id}</code>
   • Telegram ID: <code>{user.telegram_id}</code>
   • Username: @{user.username if user.username else 'не указан'}
   • Имя: {user.first_name} {user.last_name or ''}

📦 <b>Заказ #{order.id}</b>
{items_text}

💰 <b>Сумма заказа:</b> {float(order.final_amount):,.2f} ₽
💳 <b>Способ оплаты:</b> {payment.provider if payment else 'Не указан'} - {payment.payment_method if payment else ''}
🎁 <b>Бонусы использовано:</b> {float(order.bonus_used):,.2f} ₽
✨ <b>Бонусы начислено:</b> {float(order.bonus_earned):,.2f} ₽

⏰ <b>Дата:</b> {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}
"""
    
    # Отправляем всем админам
    for admin_id in admin_ids:
        try:
            await send_telegram_notification(admin_id, message)
            logger.info(f"Уведомление о заказе #{order.id} отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")


async def update_payment_status(
    payment: Payment,
    status: str,
    db: AsyncSession,
    paid_at: datetime | None = None
):
    """
    Обновить статус платежа и связанного заказа
    
    Args:
        payment: Объект платежа
        status: Новый статус (success, failed, cancelled, refunded)
        db: Сессия БД
        paid_at: Дата оплаты (для успешных платежей)
    """
    # Не обновлять, если статус уже установлен (избежать дублирования)
    if payment.status == status:
        return
    
    payment.status = status
    payment.updated_at = datetime.utcnow()
    
    if status == "success" and paid_at:
        payment.paid_at = paid_at
    elif status == "cancelled":
        payment.cancelled_at = datetime.utcnow()
    
    # Обновить статус заказа и обработать бонусы
    order_result = await db.execute(
        select(Order)
        .where(Order.id == payment.order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
    )
    order = order_result.scalar_one_or_none()
    
    if order:
        if status == "success":
            if order.status == "pending":
                order.status = "paid"
                
                # Списать бонусы пользователя (если были использованы)
                if order.bonus_used > 0:
                    user = order.user
                    if user:
                        user.bonus_balance -= order.bonus_used
                        # Создать транзакцию списания
                        bonus_spent_tx = BonusTransaction(
                            user_id=user.id,
                            order_id=order.id,
                            amount=-order.bonus_used,
                            type="spent",
                            description=f"Списание бонусов за заказ #{order.id}"
                        )
                        db.add(bonus_spent_tx)
                
                # Начислить заработанные бонусы
                if order.bonus_earned > 0:
                    user = order.user
                    if user:
                        user.bonus_balance += order.bonus_earned
                        # Создать транзакцию начисления
                        bonus_earned_tx = BonusTransaction(
                            user_id=user.id,
                            order_id=order.id,
                            amount=order.bonus_earned,
                            type="earned",
                            description=f"Начисление бонусов за заказ #{order.id}"
                        )
                        db.add(bonus_earned_tx)
                
                # Обновить статистику пользователя (только при успешной оплате!)
                user = order.user
                if user:
                    user.total_spent += order.final_amount  # Добавляем к "всего потрачено"
                    user.total_orders += 1  # Увеличиваем счетчик заказов
                
                # Отправить уведомление админам о покупке
                if user and order.items:
                    await notify_admins_about_purchase(user, order, order.items, payment)
                    
        elif status == "cancelled" or status == "failed":
            if order.status == "pending":
                order.status = "cancelled"
                # Вернуть товары на склад
                # ВАЖНО: Бонусы НЕ списываем и НЕ начисляем при неудачной оплате!
                order_items_result = await db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                )
                order_items = order_items_result.scalars().all()
                for item in order_items:
                    if item.product:
                        item.product.stock_count += item.quantity
    
    await db.commit()


# ==================== WEBHOOK ENDPOINTS ====================

@router.post("/webhook/freekassa")
async def freekassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook для обработки уведомлений от FreeKassa
    
    FreeKassa отправляет POST запрос с параметрами (form-data):
    - MERCHANT_ID - ID магазина
    - AMOUNT - Сумма платежа
    - MERCHANT_ORDER_ID - ID заказа
    - SIGN - Подпись (md5(MERCHANT_ID:AMOUNT:SECRET_KEY2:MERCHANT_ORDER_ID))
    - intid - Внутренний ID платежа (опционально)
    
    Документация: https://docs.freekassa.ru/
    
    После успешной обработки необходимо вернуть строку "YES"
    """
    try:
        # Получить данные из формы (FreeKassa отправляет form-data)
        form_data = await request.form()
        
        merchant_id = form_data.get("MERCHANT_ID")
        amount_str = form_data.get("AMOUNT")
        order_id_str = form_data.get("MERCHANT_ORDER_ID")
        signature = form_data.get("SIGN")
        intid = form_data.get("intid")  # Внутренний ID платежа от FreeKassa
        
        # Проверить наличие обязательных параметров
        if not all([merchant_id, amount_str, order_id_str, signature]):
            logger.warning(f"Неполные данные от FreeKassa: {dict(form_data)}")
            # FreeKassa ожидает "YES" даже при ошибке, но лучше вернуть ошибку
            return "NO"
        
        # Проверить merchant_id
        if merchant_id != settings.FREEKASSA_MERCHANT_ID:
            logger.warning(f"Неверный merchant_id: {merchant_id}, ожидался: {settings.FREEKASSA_MERCHANT_ID}")
            return "NO"
        
        order_id = int(order_id_str)
        amount = Decimal(amount_str)
        
        # Найти платеж
        payment_result = await db.execute(
            select(Payment)
            .where(Payment.order_id == order_id, Payment.provider == "freekassa")
            .options(selectinload(Payment.user), selectinload(Payment.order))
        )
        payment = payment_result.scalar_one_or_none()
        
        if not payment:
            logger.warning(f"Платеж не найден для заказа {order_id}")
            return "NO"
        
        # Проверить подпись
        # Формула: md5(MERCHANT_ID:AMOUNT:SECRET_KEY2:MERCHANT_ORDER_ID)
        provider = FreeKassaProvider(
            merchant_id=settings.FREEKASSA_MERCHANT_ID,
            secret_key=settings.FREEKASSA_SECRET_KEY,
            secret_key2=settings.FREEKASSA_SECRET_KEY2
        )
        
        if not provider.verify_webhook_signature(amount, order_id, signature):
            logger.error(f"Неверная подпись для платежа {payment.id}. Получено: {signature}")
            return "NO"
        
        # Проверить сумму (допускаем небольшую погрешность из-за округления)
        amount_diff = abs(float(payment.amount) - float(amount))
        if amount_diff > 0.01:  # Разница больше 1 копейки
            logger.error(f"Неверная сумма для платежа {payment.id}: ожидалось {payment.amount}, получено {amount}")
            return "NO"
        
        # FreeKassa отправляет уведомление только об успешной оплате
        # Если webhook пришел, значит платеж успешен
        # Обновить статус платежа на success (если еще не обновлен)
        if payment.status != "success":
            # Сохранить intid в payment_id, если он есть (внутренний ID платежа от FreeKassa)
            if intid:
                # Обновить payment_id с intid для лучшей трассировки
                payment.payment_id = f"freekassa_{intid}"
            
            await update_payment_status(payment, "success", db, paid_at=datetime.utcnow())
            
            # Отправить уведомление пользователю
            user = payment.user
            if user:
                message = f"""
✅ <b>Платеж успешно выполнен!</b>

📦 Заказ #{order_id}
💰 Сумма: {float(amount):,.2f} ₽
💳 Провайдер: FreeKassa

Ваш заказ оплачен и будет обработан в ближайшее время.
"""
                await send_telegram_notification(user.telegram_id, message)
        
        # FreeKassa ожидает ответ "YES" при успешной обработке
        return "YES"
        
    except HTTPException:
        # При HTTPException все равно вернуть "NO" для FreeKassa
        return "NO"
    except Exception as e:
        logger.error(f"Ошибка при обработке webhook FreeKassa: {e}", exc_info=True)
        return "NO"


@router.post("/webhook/paypalych")
async def paypalych_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook для обработки postback от PayPaly
    
    PayPaly отправляет POST запрос с JSON данными или form-data в формате:
    {
      "Status": "SUCCESS" или "FAIL",
      "InvId": "order_id",
      "OutSum": "amount",
      "TrsId": "bill_id",
      "SignatureValue": "signature",
      ...
    }
    """
    try:
        logger.info(f"===== PAYPALYCH WEBHOOK RECEIVED =====")
        logger.info(f"Content-Type: {request.headers.get('content-type')}")
        
        # Получить raw body для отладки
        body = await request.body()
        logger.info(f"Raw body: {body}")
        
        # Попытка распарсить как JSON
        data = {}
        try:
            data = await request.json()
            logger.info(f"Parsed as JSON: {data}")
        except:
            # Если не JSON, пробуем form-data
            logger.info("Failed to parse as JSON, trying form-data...")
            form_data = await request.form()
            data = dict(form_data)
            logger.info(f"Parsed as form-data: {data}")
        
        if not data:
            logger.error("Empty data received")
            raise HTTPException(status_code=400, detail="Empty data")
        
        # Формат postback от Paypalych
        status = data.get("Status")  # "SUCCESS" или "FAIL"
        order_id_str = data.get("InvId")  # order_id в формате строки
        
        # ВАЖНО: OutSum - это сумма С комиссией (то, что заплатил пользователь)
        # BalanceAmount - это сумма БЕЗ комиссии (то, что придет на баланс)
        # Используем BalanceAmount для сравнения с суммой в базе
        balance_amount_str = data.get("BalanceAmount")  # сумма без комиссии
        out_sum_str = data.get("OutSum")  # сумма с комиссией
        commission_str = data.get("Commission")  # комиссия
        
        amount_str = balance_amount_str or out_sum_str  # Приоритет - BalanceAmount
        
        bill_id = data.get("TrsId")  # bill_id (ID платежа)
        signature = data.get("SignatureValue")  # подпись
        
        if not all([order_id_str, amount_str, status]):
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Парсим order_id (может быть строкой типа "Заказ 123" или просто числом)
        try:
            # Пробуем извлечь число из строки
            order_id_match = re.search(r'\d+', str(order_id_str))
            if order_id_match:
                order_id = int(order_id_match.group())
            else:
                order_id = int(order_id_str)
        except (ValueError, AttributeError):
            logger.error(f"Не удалось распарсить order_id из {order_id_str}")
            raise HTTPException(status_code=400, detail="Invalid order_id format")
        
        amount = Decimal(amount_str)
        
        # Найти платеж по order_id или bill_id
        payment_result = await db.execute(
            select(Payment)
            .where(
                (Payment.order_id == order_id) & (Payment.provider == "paypalych")
            )
            .options(selectinload(Payment.user), selectinload(Payment.order))
        )
        payment = payment_result.scalar_one_or_none()
        
        # Если не нашли по order_id, пробуем найти по bill_id (payment_id)
        if not payment and bill_id:
            payment_result = await db.execute(
                select(Payment)
                .where(
                    (Payment.payment_id == bill_id) & (Payment.provider == "paypalych")
                )
                .options(selectinload(Payment.user), selectinload(Payment.order))
            )
            payment = payment_result.scalar_one_or_none()
        
        if not payment:
            logger.warning(f"Платеж не найден для заказа {order_id} или bill_id {bill_id}")
            return {"status": "error", "message": "Payment not found"}
        
        # Проверить подпись (если требуется)
        if signature:
            provider = PaypalychProvider(
                api_key=settings.PAYPALYCH_API_KEY,
                shop_id=settings.PAYPALYCH_SHOP_ID
            )
            if not provider.verify_webhook_signature(order_id_str, amount_str, signature):
                logger.error(f"Неверная подпись для платежа {payment.id}")
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Проверить сумму (допускаем небольшую погрешность)
        # Сравниваем с BalanceAmount (сумма без комиссии)
        amount_diff = abs(float(payment.amount) - float(amount))
        if amount_diff > 0.01:  # Разница больше 1 копейки
            logger.error(
                f"Неверная сумма для платежа {payment.id}: "
                f"ожидалось {payment.amount}, получено {amount} "
                f"(BalanceAmount={balance_amount_str}, OutSum={out_sum_str}, Commission={commission_str})"
            )
            raise HTTPException(status_code=400, detail="Amount mismatch")
        
        # Обновить статус платежа
        # Status: "SUCCESS" -> success, "FAIL" -> failed
        if status.upper() == "SUCCESS":
            logger.info(f"Payment SUCCESS for order {order_id}, updating status...")
            await update_payment_status(payment, "success", db, paid_at=datetime.utcnow())
            logger.info(f"Payment status updated, bonus_earned: {payment.order.bonus_earned if payment.order else 'N/A'}")
            
            # Отправить уведомление пользователю
            user = payment.user
            if user:
                message = f"""
✅ <b>Платеж успешно выполнен!</b>

📦 Заказ #{order_id}
💰 Сумма: {float(amount):,.2f} ₽
💳 Провайдер: PayPaly

Ваш заказ оплачен и будет обработан в ближайшее время.
"""
                await send_telegram_notification(user.telegram_id, message)
        elif status.upper() == "FAIL":
            await update_payment_status(payment, "failed", db)
            
            # Отправить уведомление об ошибке
            user = payment.user
            if user:
                message = f"""
❌ <b>Ошибка при оплате</b>

📦 Заказ #{order_id}
💰 Сумма: {float(amount):,.2f} ₽
💳 Провайдер: PayPaly

Платеж не был выполнен. Пожалуйста, попробуйте еще раз.
"""
                await send_telegram_notification(user.telegram_id, message)
        else:
            logger.warning(f"Неизвестный статус от Paypalych: {status}")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке webhook PayPaly: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order/{order_id}/cancel")
async def cancel_order_notification(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Уведомление об отмене заказа (вызывается из веб-приложения)
    """
    try:
        # Найти заказ
        order_result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.user))
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Найти платеж
        payment_result = await db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalar_one_or_none()
        
        # Обновить статус заказа
        if order.status == "pending":
            order.status = "cancelled"
            
            # Вернуть товары на склад
            order_items_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order_items = order_items_result.scalars().all()
            for item in order_items:
                if item.product:
                    item.product.stock_count += item.quantity
            
            await db.commit()
            
            # Обновить статус платежа, если есть
            if payment:
                await update_payment_status(payment, "cancelled", db)
            
            # Отправить уведомление пользователю
            user = order.user
            if user:
                message = f"""
❌ <b>Заказ отменен</b>

📦 Заказ #{order_id}
💰 Сумма: {float(order.total_amount):,.2f} ₽

Заказ был отменен. Товары возвращены на склад.
"""
                await send_telegram_notification(user.telegram_id, message)
            
            return {"status": "success", "message": "Order cancelled"}
        else:
            return {"status": "error", "message": f"Cannot cancel order with status {order.status}"}
            
    except Exception as e:
        logger.error(f"Ошибка при отмене заказа {order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
