"""
Конфигурация приложения через pydantic-settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Настройки приложения из .env"""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tg_shop"

    # Telegram Bot
    BOT_TOKEN: str
    # Для проверки initData (обычно совпадает с BOT_TOKEN)
    TG_WEBAPP_BOT_TOKEN: str

    # Security
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24 * 30  # 30 дней
    ENCRYPTION_KEY: str = "change-me-in-production-32-chars"

    # Admin
    OWNER_TG_IDS: str = ""  # CSV строка, например "123456,789012"

    # API
    API_PUBLIC_URL: str = "http://localhost:8000"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = ""  # URL веб-приложения для кнопки в боте

    # App
    DEBUG: bool = False

    # Payment Providers - FreeKassa
    FREEKASSA_MERCHANT_ID: str = ""
    FREEKASSA_SECRET_KEY: str = ""  # Secret Key 1
    FREEKASSA_SECRET_KEY2: str = ""  # Secret Key 2

    # Payment Providers - PayPaly
    PAYPALYCH_API_KEY: str = ""
    PAYPALYCH_SECRET_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def owner_ids(self) -> List[int]:
        """Парсинг OWNER_TG_IDS в список int"""
        if not self.OWNER_TG_IDS:
            return []
        return [int(x.strip()) for x in self.OWNER_TG_IDS.split(",") if x.strip()]


# Глобальный инстанс настроек
settings = Settings()
