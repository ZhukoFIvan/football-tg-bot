"""
Утилиты для работы с файлами и изображениями
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException


# Директория для загрузки файлов
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Поддерживаемые форматы изображений
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Максимальный размер файла (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


async def save_upload_file(file: UploadFile, subfolder: str = "") -> str:
    """
    Сохранить загруженный файл и вернуть относительный путь

    Args:
        file: Загруженный файл
        subfolder: Подпапка для организации файлов (sections, products, banners и т.д.)

    Returns:
        Относительный путь к сохраненному файлу
    """
    # Проверка расширения
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Создать подпапку если нужно
    target_dir = UPLOAD_DIR / subfolder if subfolder else UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # Генерировать уникальное имя файла
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = target_dir / unique_filename

    # Сохранить файл
    content = await file.read()

    # Проверка размера
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    with open(file_path, "wb") as f:
        f.write(content)

    # Вернуть относительный путь (для сохранения в БД)
    relative_path = str(file_path.relative_to(UPLOAD_DIR.parent))
    return f"/{relative_path}"


def delete_file(file_path: str) -> bool:
    """
    Удалить файл по пути

    Args:
        file_path: Путь к файлу (например "/uploads/sections/abc.jpg")

    Returns:
        True если файл удален, False если файл не найден
    """
    try:
        # Убрать ведущий слэш и построить полный путь
        clean_path = file_path.lstrip("/")
        full_path = Path(clean_path)

        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        return False
    except Exception:
        return False


def get_file_url(file_path: Optional[str], base_url: str) -> Optional[str]:
    """
    Получить полный URL файла

    Args:
        file_path: Относительный путь к файлу
        base_url: Базовый URL API (из settings.API_PUBLIC_URL)

    Returns:
        Полный URL или None
    """
    if not file_path:
        return None

    # Если путь уже полный URL - вернуть как есть
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path

    # Собрать URL
    return f"{base_url.rstrip('/')}{file_path}"
