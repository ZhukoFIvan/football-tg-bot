#!/bin/bash

# Скрипт для резервного копирования базы данных

set -e

# Директория для бэкапов
BACKUP_DIR="$HOME/backups/tg-shop"
mkdir -p "$BACKUP_DIR"

# Имя файла с датой
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

echo "📦 Creating database backup..."

# Создание бэкапа
cd "$(dirname "$0")/.."
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U postgres tg_shop > "$BACKUP_FILE"

# Сжатие
gzip "$BACKUP_FILE"

echo "✅ Backup created: ${BACKUP_FILE}.gz"

# Удаление старых бэкапов (старше 30 дней)
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete

echo "🧹 Old backups cleaned up"
echo ""
echo "📊 Available backups:"
ls -lh "$BACKUP_DIR"
