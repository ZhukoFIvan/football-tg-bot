"""
REST API для чатов — список, история, смена статуса
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.db.session import get_db
from core.db.models import Chat, ChatMessage, Order, OrderItem, User
from core.dependencies import get_current_user, get_admin_user
from apps.socket.server import sio

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Схемы ответов
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: Optional[int]
    sender_type: str
    content: str
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    product_title: str
    quantity: int
    price: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    status: str
    final_amount: float
    created_at: str
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    display_name: Optional[str]
    username: Optional[str]
    first_name: Optional[str]

    class Config:
        from_attributes = True


class ChatOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    status: str
    created_at: str
    updated_at: str
    unread_count: int = 0
    last_message: Optional[str] = None
    order: Optional[OrderOut] = None
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _chat_to_dict(chat: Chat, current_user_id: int, is_admin: bool) -> dict:
    opposite = "admin" if not is_admin else "user"
    unread = sum(1 for m in chat.messages if not m.is_read and m.sender_type == opposite)
    last_msg = chat.messages[-1].content if chat.messages else None

    order_out = None
    if chat.order:
        order_out = {
            "id": chat.order.id,
            "status": chat.order.status,
            "final_amount": float(chat.order.final_amount),
            "created_at": chat.order.created_at.isoformat(),
            "items": [
                {
                    "product_title": item.product_title,
                    "quantity": item.quantity,
                    "price": float(item.price),
                }
                for item in (chat.order.items or [])
            ],
        }

    user_out = None
    if chat.user:
        user_out = {
            "id": chat.user.id,
            "display_name": chat.user.display_name,
            "username": chat.user.username,
            "first_name": chat.user.first_name,
        }

    return {
        "id": chat.id,
        "order_id": chat.order_id,
        "user_id": chat.user_id,
        "status": chat.status,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "unread_count": unread,
        "last_message": last_msg,
        "order": order_out,
        "user": user_out,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def get_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Список чатов.
    Пользователь видит только свои; админ — все.
    """
    is_admin = current_user.is_admin
    query = (
        select(Chat)
        .options(
            selectinload(Chat.messages),
            selectinload(Chat.order).selectinload(Order.items),
            selectinload(Chat.user),
        )
        .order_by(desc(Chat.updated_at))
    )
    if not is_admin:
        query = query.where(Chat.user_id == current_user.id)

    result = await db.execute(query)
    chats = result.scalars().all()

    return [_chat_to_dict(c, current_user.id, is_admin) for c in chats]


@router.get("/{chat_id}")
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Детали чата + история сообщений"""
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id)
        .options(
            selectinload(Chat.messages),
            selectinload(Chat.order).selectinload(Order.items),
            selectinload(Chat.user),
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if not current_user.is_admin and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _chat_to_dict(chat, current_user.id, current_user.is_admin)


@router.post("/{chat_id}/resolve")
async def resolve_chat(
    chat_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Товар доставлен → status=resolved + системное сообщение"""
    result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.status = "resolved"
    chat.updated_at = datetime.utcnow()

    msg = ChatMessage(
        chat_id=chat_id,
        sender_id=None,
        sender_type="system",
        content="✅ Товар передан. Заказ выполнен! Спасибо за покупку.",
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Socket.IO уведомление участникам чата
    await sio.emit("new_message", {
        "id": msg.id, "chat_id": chat_id, "sender_id": None,
        "sender_type": "system", "content": msg.content,
        "is_read": False, "created_at": msg.created_at.isoformat(),
    }, room=f"chat_{chat_id}")
    await sio.emit("chat_status_changed", {"chat_id": chat_id, "status": "resolved"},
                   room=f"chat_{chat_id}")

    return {"ok": True, "status": "resolved"}


@router.post("/{chat_id}/close")
async def close_chat(
    chat_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Закрыть чат"""
    result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.status = "closed"
    chat.updated_at = datetime.utcnow()
    await db.commit()

    await sio.emit("chat_status_changed", {"chat_id": chat_id, "status": "closed"},
                   room=f"chat_{chat_id}")

    return {"ok": True, "status": "closed"}
