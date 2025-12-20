#!/bin/bash

# Скрипт для локальной разработки и тестирования

set -e

echo "🔄 Обновление локального окружения..."

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка что мы в корне проекта
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Ошибка: docker-compose.yml не найден${NC}"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Остановить контейнеры
echo -e "${BLUE}🛑 Остановка контейнеров...${NC}"
docker compose down

# Пересобрать образы
echo -e "${BLUE}🔨 Пересборка образов...${NC}"
docker compose build --no-cache

# Запустить контейнеры
echo -e "${BLUE}🚀 Запуск контейнеров...${NC}"
docker compose up -d

# Подождать запуска БД
echo -e "${BLUE}⏳ Ожидание запуска базы данных...${NC}"
sleep 5

# Применить миграции
echo -e "${BLUE}📦 Применение миграций...${NC}"
docker compose exec api alembic upgrade head

# Показать статус
echo -e "${BLUE}📊 Статус контейнеров:${NC}"
docker compose ps

echo ""
echo -e "${GREEN}✅ Готово!${NC}"
echo ""
echo -e "${BLUE}📝 Полезные команды:${NC}"
echo "  docker compose logs -f api     # Логи API"
echo "  docker compose logs -f bot     # Логи бота"
echo "  docker compose logs -f         # Все логи"
echo "  docker compose ps              # Статус контейнеров"
echo "  docker compose down            # Остановить всё"
echo ""
echo -e "${BLUE}🌐 Доступ:${NC}"
echo "  API:     http://localhost:8000"
echo "  Swagger: http://localhost:8000/docs"
echo "  Health:  http://localhost:8000/health"
echo ""
