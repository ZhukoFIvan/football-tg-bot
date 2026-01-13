#!/bin/bash
# Скрипт для проверки количества пользователей

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Проверка через Docker
if command -v docker-compose &> /dev/null && docker-compose ps | grep -q "Up"; then
    echo "🔍 Проверка через Docker..."
    docker-compose exec api python scripts/check_users_count.py
else
    # Проверка через виртуальное окружение
    if [ -d "venv" ]; then
        echo "🔍 Проверка через виртуальное окружение..."
        ./venv/bin/python scripts/check_users_count.py
    else
        echo "❌ Не найдено ни Docker, ни виртуальное окружение"
        echo "💡 Создайте виртуальное окружение или запустите Docker"
        exit 1
    fi
fi
