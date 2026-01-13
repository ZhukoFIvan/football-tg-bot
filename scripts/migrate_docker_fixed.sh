#!/bin/bash
# Скрипт для запуска миграции через Docker контейнер

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Проверка наличия shop.db
if [ ! -f "shop.db" ]; then
    echo "❌ Файл shop.db не найден в корне проекта!"
    echo "💡 Убедитесь что файл находится в: $PROJECT_ROOT/shop.db"
    exit 1
fi

# Проверка что Docker контейнеры запущены
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker контейнеры не запущены!"
    echo "💡 Запустите: docker-compose up -d"
    exit 1
fi

# Проверка режима запуска
DRY_RUN=${1:-"--dry-run"}

echo "🔍 Запуск миграции через Docker контейнер..."
echo ""

if [ "$DRY_RUN" = "--dry-run" ] || [ "$DRY_RUN" = "-d" ]; then
    echo "⚠️  РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут применены"
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

echo ""
echo "✅ Готово!"
