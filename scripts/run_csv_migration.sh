#!/bin/bash
# Скрипт для запуска миграции из CSV файла

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Проверка наличия CSV файла
CSV_FILE=${1:-"report_542432_part1.csv"}

if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Файл $CSV_FILE не найден в корне проекта!"
    echo "💡 Убедитесь что файл находится в: $PROJECT_ROOT/$CSV_FILE"
    exit 1
fi

echo "📋 Файл CSV: $CSV_FILE"
echo ""

# Проверка режима запуска
DRY_RUN=${2:-"--dry-run"}

# Проверка что Docker контейнеры запущены
if docker-compose ps | grep -q "Up"; then
    echo "🐳 Запуск через Docker контейнер..."
    
    # Копируем CSV файл в контейнер если нужно
    docker cp "$CSV_FILE" tg_shop_api:/app/"$CSV_FILE" 2>/dev/null || true
    
    if [ "$DRY_RUN" = "--dry-run" ] || [ "$DRY_RUN" = "-d" ]; then
        echo "⚠️  РЕЖИМ ПРОВЕРКИ (dry-run)"
        docker-compose exec -T api python scripts/migrate_from_csv.py --csv-file "$CSV_FILE" --dry-run
    else
        echo "⚠️  Запуск РЕАЛЬНОЙ миграции..."
        read -p "Вы уверены? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "❌ Миграция отменена"
            exit 0
        fi
        docker-compose exec -T api python scripts/migrate_from_csv.py --csv-file "$CSV_FILE"
    fi
else
    echo "💻 Запуск через виртуальное окружение..."
    
    # Проверка наличия виртуального окружения
    if [ ! -d "venv" ]; then
        echo "❌ Виртуальное окружение не найдено!"
        echo "💡 Создайте: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    
    source venv/bin/activate
    
    if [ "$DRY_RUN" = "--dry-run" ] || [ "$DRY_RUN" = "-d" ]; then
        echo "⚠️  РЕЖИМ ПРОВЕРКИ (dry-run)"
        python scripts/migrate_from_csv.py --csv-file "$CSV_FILE" --dry-run
    else
        echo "⚠️  Запуск РЕАЛЬНОЙ миграции..."
        read -p "Вы уверены? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "❌ Миграция отменена"
            exit 0
        fi
        python scripts/migrate_from_csv.py --csv-file "$CSV_FILE"
    fi
fi

echo ""
echo "✅ Готово!"
