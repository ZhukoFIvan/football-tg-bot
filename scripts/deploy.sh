#!/bin/bash

# Скрипт для быстрого деплоя обновлений

set -e

echo "🚀 Starting deployment..."

# Переход в директорию проекта
cd "$(dirname "$0")/.."

# Получение обновлений (если используется Git)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull origin main
fi

# Остановка контейнеров
echo "🛑 Stopping containers..."
docker compose -f docker-compose.prod.yml down

# Сборка образов
echo "🔨 Building images..."
docker compose -f docker-compose.prod.yml build --no-cache

# Запуск контейнеров
echo "▶️  Starting containers..."
docker compose -f docker-compose.prod.yml up -d

# Ожидание запуска БД
echo "⏳ Waiting for database..."
sleep 10

# Применение миграций
echo "🗄️  Running migrations..."
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# Проверка статуса
echo "✅ Checking status..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "✨ Deployment completed!"
echo ""
echo "📊 View logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔍 Check health:"
echo "  curl http://localhost:8000/health"
