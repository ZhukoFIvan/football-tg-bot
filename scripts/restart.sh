#!/bin/bash

# Быстрый перезапуск сервисов

# Цвета
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo -e "${BLUE}🔄 Перезапуск всех сервисов...${NC}"
    docker compose restart
    echo -e "${GREEN}✅ Готово!${NC}"
else
    echo -e "${BLUE}🔄 Перезапуск $SERVICE...${NC}"
    docker compose restart $SERVICE
    echo -e "${GREEN}✅ $SERVICE перезапущен!${NC}"
    echo ""
    echo -e "${BLUE}📋 Логи:${NC}"
    docker compose logs -f --tail=50 $SERVICE
fi
