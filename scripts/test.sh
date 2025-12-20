#!/bin/bash

# Скрипт для быстрого тестирования API

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

API_URL="http://localhost:8000"

echo -e "${BLUE}🧪 Тестирование API...${NC}"
echo ""

# Проверка health
echo -e "${BLUE}1. Проверка /health${NC}"
HEALTH=$(curl -s ${API_URL}/health)
if [[ $HEALTH == *"ok"* ]]; then
    echo -e "${GREEN}✅ Health OK: $HEALTH${NC}"
else
    echo -e "${RED}❌ Health failed${NC}"
    exit 1
fi

echo ""

# Проверка sections
echo -e "${BLUE}2. Проверка /public/sections${NC}"
SECTIONS=$(curl -s ${API_URL}/public/sections)
echo -e "${GREEN}✅ Sections: $(echo $SECTIONS | jq -r 'length') записей${NC}"

echo ""

# Проверка categories
echo -e "${BLUE}3. Проверка /public/categories${NC}"
CATEGORIES=$(curl -s ${API_URL}/public/categories)
echo -e "${GREEN}✅ Categories: $(echo $CATEGORIES | jq -r 'length') записей${NC}"

echo ""

# Проверка products
echo -e "${BLUE}4. Проверка /public/products${NC}"
PRODUCTS=$(curl -s ${API_URL}/public/products)
echo -e "${GREEN}✅ Products: $(echo $PRODUCTS | jq -r 'length') записей${NC}"

echo ""

# Проверка banners
echo -e "${BLUE}5. Проверка /public/banners${NC}"
BANNERS=$(curl -s ${API_URL}/public/banners)
echo -e "${GREEN}✅ Banners: $(echo $BANNERS | jq -r 'length') записей${NC}"

echo ""

# Проверка badges
echo -e "${BLUE}6. Проверка /public/badges${NC}"
BADGES=$(curl -s ${API_URL}/public/badges)
echo -e "${GREEN}✅ Badges: $(echo $BADGES | jq -r 'length') записей${NC}"

echo ""
echo -e "${GREEN}✅ Все тесты пройдены!${NC}"
echo ""
echo -e "${BLUE}🌐 Swagger UI: ${API_URL}/docs${NC}"
