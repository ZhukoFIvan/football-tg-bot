"""
Socket.IO сервер для чата в реальном времени.

Комнаты:
  chat_{id}  — участники конкретного чата
  admins     — все подключённые администраторы

События client→server:
  join_chat      { chat_id }
  send_message   { chat_id, content }
  mark_read      { chat_id }

События server→client:
  chat_history         { chat_id, messages }
  new_message          { message }
  new_chat             { chat }         (только комната admins)
  chat_status_changed  { chat_id, status }
  messages_read        { chat_id }
  error                { message }
"""
import logging
import socketio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from core.auth import verify_jwt_token
from core.db.session import async_session_factory
from core.db.models import Chat, ChatMessage, User
from core.config import settings

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# sid → { user_id, is_admin }
_sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg_to_dict(msg: ChatMessage) -> dict:
    from core.config import settings
    media_url = msg.media_url
    if media_url and not media_url.startswith("http"):
        media_url = f"{settings.API_PUBLIC_URL}{media_url}"
    return {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "sender_type": msg.sender_type,
        "content": msg.content,
        "message_type": msg.message_type or "text",
        "media_url": media_url,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------

@sio.event
async def connect(sid: str, environ, auth):
    token = (auth or {}).get("token")
    if not token:
        raise ConnectionRefusedError("Authentication required")

    payload = verify_jwt_token(token)
    if not payload:
        raise ConnectionRefusedError("Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise ConnectionRefusedError("Invalid token payload")

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user or user.is_banned:
        raise ConnectionRefusedError("User not found or banned")

    is_admin = (
        user.is_admin
        or (user.telegram_id is not None and user.telegram_id in settings.owner_ids)
        or (user.email is not None and user.email.lower() in settings.owner_emails)
    )
    _sessions[sid] = {"user_id": user_id, "is_admin": is_admin}

    if is_admin:
        await sio.enter_room(sid, "admins")
        logger.info(f"Admin {user_id} connected: {sid}")
    else:
        logger.info(f"User {user_id} connected: {sid}")


@sio.event
async def disconnect(sid: str):
    _sessions.pop(sid, None)


# ---------------------------------------------------------------------------
# join_chat
# ---------------------------------------------------------------------------

@sio.event
async def join_chat(sid: str, data: dict):
    session = _sessions.get(sid)
    if not session:
        return

    chat_id = data.get("chat_id")
    if not chat_id:
        return

    async with async_session_factory() as db:
        result = await db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.messages))
        )
        chat = result.scalar_one_or_none()

    if not chat:
        await sio.emit("error", {"message": "Chat not found"}, to=sid)
        return

    # Пользователь только в свой чат; админ — в любой
    if not session["is_admin"] and chat.user_id != session["user_id"]:
        await sio.emit("error", {"message": "Access denied"}, to=sid)
        return

    room = f"chat_{chat_id}"
    await sio.enter_room(sid, room)

    history = [_msg_to_dict(m) for m in chat.messages]
    await sio.emit("chat_history", {"chat_id": chat_id, "messages": history}, to=sid)

    # Помечаем входящие сообщения прочитанными
    opposite_type = "admin" if not session["is_admin"] else "user"
    async with async_session_factory() as db:
        msgs_result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_read == False,
                ChatMessage.sender_type == opposite_type,
            )
        )
        for m in msgs_result.scalars().all():
            m.is_read = True
        await db.commit()


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

@sio.event
async def send_message(sid: str, data: dict):
    session = _sessions.get(sid)
    if not session:
        return

    chat_id = data.get("chat_id")
    content = (data.get("content") or "").strip()
    media_url = (data.get("media_url") or "").strip() or None
    message_type = "image" if media_url else "text"

    # Для текстового сообщения контент обязателен; для изображения — нет
    if not chat_id or (not content and not media_url):
        return

    async with async_session_factory() as db:
        result = await db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()

        if not chat or chat.status == "closed":
            await sio.emit("error", {"message": "Chat is closed or not found"}, to=sid)
            return

        if not session["is_admin"] and chat.user_id != session["user_id"]:
            await sio.emit("error", {"message": "Access denied"}, to=sid)
            return

        sender_type = "admin" if session["is_admin"] else "user"
        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=session["user_id"],
            sender_type=sender_type,
            content=content or "",
            message_type=message_type,
            media_url=media_url,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(msg)
        chat.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(msg)

    await sio.emit("new_message", _msg_to_dict(msg), room=f"chat_{chat_id}")


# ---------------------------------------------------------------------------
# mark_read
# ---------------------------------------------------------------------------

@sio.event
async def mark_read(sid: str, data: dict):
    session = _sessions.get(sid)
    if not session:
        return

    chat_id = data.get("chat_id")
    if not chat_id:
        return

    async with async_session_factory() as db:
        result = await db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            return

        opposite_type = "admin" if not session["is_admin"] else "user"
        msgs_result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_read == False,
                ChatMessage.sender_type == opposite_type,
            )
        )
        for m in msgs_result.scalars().all():
            m.is_read = True
        await db.commit()

    await sio.emit("messages_read", {"chat_id": chat_id}, room=f"chat_{chat_id}")
