#!/bin/bash
# Скрипт для создания виртуального окружения на сервере

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Настройка виртуального окружения..."
echo ""

cd "$PROJECT_ROOT"

# Проверка наличия python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите его:"
    echo "   sudo apt update && sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Создание виртуального окружения если его нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
else
    echo "✅ Виртуальное окружение уже существует"
fi

# Активация и установка зависимостей
echo ""
echo "📥 Установка зависимостей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Готово! Виртуальное окружение настроено."
echo ""
echo "💡 Для использования активируйте окружение:"
echo "   source venv/bin/activate"
echo ""
echo "💡 Затем запустите скрипт миграции:"
echo "   python scripts/migrate_from_sqlite.py --sqlite-db shop.db --dry-run"
