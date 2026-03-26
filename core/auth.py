"""
Утилиты для авторизации через Telegram WebApp initData, Telegram Login Widget, JWT и пароли
"""
import hashlib
import hmac
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from urllib.parse import parse_qs
from core.config import settings

import bcrypt as _bcrypt_lib


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Хешировать пароль через bcrypt"""
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Проверить пароль"""
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Telegram WebApp initData (Mini App)
# ---------------------------------------------------------------------------

def verify_telegram_webapp_data(init_data: str) -> Optional[Dict]:
    """
    Проверка initData от Telegram WebApp

    Алгоритм:
    1. Парсим query string
    2. Извлекаем hash
    3. Создаем data_check_string из остальных параметров (sorted)
    4. Вычисляем HMAC-SHA-256 с secret_key = HMAC-SHA-256(BOT_TOKEN, "WebAppData")
    5. Сравниваем с переданным hash

    Возвращает словарь с данными пользователя или None если невалидно
    """
    try:
        # Парсим query string
        parsed = parse_qs(init_data)

        # Извлекаем hash
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None

        # Удаляем hash из параметров
        data_check_arr = []
        for key, values in sorted(parsed.items()):
            if key == "hash":
                continue
            for value in values:
                data_check_arr.append(f"{key}={value}")

        data_check_string = "\n".join(data_check_arr)

        # Создаем secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.TG_WEBAPP_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Вычисляем hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Сравниваем
        if calculated_hash != received_hash:
            return None

        # Парсим user данные
        user_data = parsed.get("user", [None])[0]
        if user_data:
            import json
            return json.loads(user_data)

        return {}
    except Exception as e:
        print(f"Error verifying Telegram WebApp data: {e}")
        return None


# ---------------------------------------------------------------------------
# Telegram Login Widget (сайт)
# ---------------------------------------------------------------------------

def verify_telegram_widget_data(data: Dict) -> bool:
    """
    Проверка данных от Telegram Login Widget (виджет на сайте, не Mini App).

    Алгоритм отличается от WebApp:
    - secret_key = SHA256(BOT_TOKEN) — без "WebAppData"
    - auth_date не должен быть старше 24 часов
    """
    try:
        received_hash = data.get("hash")
        if not received_hash:
            return False

        # Проверяем свежесть auth_date (не старше 24 часов)
        auth_date = int(data.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            return False

        # Формируем data_check_string (все поля кроме hash, сортировка по ключу)
        check_items = []
        for key in sorted(data.keys()):
            if key == "hash":
                continue
            check_items.append(f"{key}={data[key]}")
        data_check_string = "\n".join(check_items)

        # secret_key = SHA256(BOT_TOKEN)
        secret_key = hashlib.sha256(settings.TG_WEBAPP_BOT_TOKEN.encode()).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        return calculated_hash == received_hash
    except Exception as e:
        print(f"Error verifying Telegram widget data: {e}")
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_jwt_token(user_id: int, telegram_id: Optional[int] = None) -> str:
    """
    Создание JWT токена. telegram_id опционален (веб-пользователи без TG).
    """
    payload: Dict = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    if telegram_id is not None:
        payload["telegram_id"] = telegram_id

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def verify_jwt_token(token: str) -> Optional[Dict]:
    """
    Проверка JWT токена
    Возвращает payload или None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
