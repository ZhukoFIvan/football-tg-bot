#!/bin/bash
# Скрипт для запуска миграции через Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Проверка наличия shop.db
if [ ! -f "shop.db" ]; then
    echo "❌ Файл shop.db не найден в корне проекта!"
    exit 1
fi

# Проверка режима (dry-run или реальная миграция)
DRY_RUN=${1:-"--dry-run"}

if [ "$DRY_RUN" = "--dry-run" ] || [ "$DRY_RUN" = "-d" ]; then
    echo "🔍 Запуск миграции в режиме проверки (dry-run)..."
    docker-compose exec -T api python scripts/migrate_from_sqlite.py --sqlite-db shop.db --dry-run
else
    echo "⚠️  Запуск РЕАЛЬНОЙ миграции..."
    read -p "Вы уверены? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Миграция отменена"
        exit 0
    fi
    docker-compose exec -T api python scripts/migrate_from_sqlite.py --sqlite-db shop.db
fi
