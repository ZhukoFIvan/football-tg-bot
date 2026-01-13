#!/bin/bash
# Скрипт для запуска миграции с автоматической активацией окружения

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Проверка наличия shop.db
if [ ! -f "shop.db" ]; then
    echo "❌ Файл shop.db не найден в корне проекта!"
    exit 1
fi

# Проверка наличия виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Виртуальное окружение не найдено. Создаю..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
fi

# Использование Python из виртуального окружения напрямую
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
VENV_PIP="$PROJECT_ROOT/venv/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Python из виртуального окружения не найден!"
    exit 1
fi

echo "🔌 Использование Python из виртуального окружения: $VENV_PYTHON"

# Проверка и установка зависимостей
if ! $VENV_PYTHON -c "import sqlalchemy" 2>/dev/null; then
    echo "📥 Установка зависимостей..."
    $VENV_PIP install --upgrade pip --quiet
    $VENV_PIP install -r requirements.txt
    echo "✅ Зависимости установлены"
else
    echo "✅ Зависимости уже установлены"
fi

# Проверка режима запуска
DRY_RUN=${1:-"--dry-run"}

echo ""
if [ "$DRY_RUN" = "--dry-run" ] || [ "$DRY_RUN" = "-d" ]; then
    echo "🔍 Запуск миграции в режиме проверки (dry-run)..."
    $VENV_PYTHON scripts/migrate_from_sqlite.py --sqlite-db shop.db --dry-run
else
    echo "⚠️  Запуск РЕАЛЬНОЙ миграции..."
    read -p "Вы уверены? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Миграция отменена"
        exit 0
    fi
    $VENV_PYTHON scripts/migrate_from_sqlite.py --sqlite-db shop.db
fi

echo ""
echo "✅ Готово!"
