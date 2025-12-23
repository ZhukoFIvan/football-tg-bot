#!/bin/bash

# Скрипт для загрузки изображений через API

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

API_URL="http://localhost:8000"
JWT_TOKEN=""

# Функция для получения JWT токена
get_token() {
    echo -e "${BLUE}🔐 Получение JWT токена...${NC}"
    
    # Здесь нужно получить initData от Telegram
    # Для локальной разработки можно использовать тестовый токен
    
    echo -e "${RED}⚠️  Для загрузки изображений нужен JWT токен админа${NC}"
    echo -e "${BLUE}Получите токен через:${NC}"
    echo "1. Откройте Swagger: http://localhost:8000/docs"
    echo "2. Авторизуйтесь через POST /auth/telegram"
    echo "3. Скопируйте access_token"
    echo ""
    read -p "Введите JWT токен: " JWT_TOKEN
}

# Функция для загрузки изображения секции
upload_section_image() {
    local section_id=$1
    local image_path=$2
    
    echo -e "${BLUE}📤 Загрузка изображения для секции #${section_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${API_URL}/admin/sections/${section_id}/image" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -F "file=@${image_path}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Успешно загружено!${NC}"
        echo "$body" | jq '.'
    else
        echo -e "${RED}❌ Ошибка: HTTP $http_code${NC}"
        echo "$body"
    fi
}

# Функция для загрузки изображения категории
upload_category_image() {
    local category_id=$1
    local image_path=$2
    
    echo -e "${BLUE}📤 Загрузка изображения для категории #${category_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${API_URL}/admin/categories/${category_id}/image" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -F "file=@${image_path}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Успешно загружено!${NC}"
        echo "$body" | jq '.'
    else
        echo -e "${RED}❌ Ошибка: HTTP $http_code${NC}"
        echo "$body"
    fi
}

# Функция для загрузки изображения товара
upload_product_image() {
    local product_id=$1
    local image_path=$2
    
    echo -e "${BLUE}📤 Загрузка изображения для товара #${product_id}...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${API_URL}/admin/products/${product_id}/image" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -F "file=@${image_path}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Успешно загружено!${NC}"
        echo "$body" | jq '.'
    else
        echo -e "${RED}❌ Ошибка: HTTP $http_code${NC}"
        echo "$body"
    fi
}

# Меню
echo -e "${BLUE}📸 Загрузка изображений${NC}"
echo ""
echo "1. Загрузить изображение секции"
echo "2. Загрузить изображение категории"
echo "3. Загрузить изображение товара"
echo ""
read -p "Выберите действие (1-3): " action

get_token

case $action in
    1)
        read -p "ID секции: " section_id
        read -p "Путь к изображению: " image_path
        upload_section_image "$section_id" "$image_path"
        ;;
    2)
        read -p "ID категории: " category_id
        read -p "Путь к изображению: " image_path
        upload_category_image "$category_id" "$image_path"
        ;;
    3)
        read -p "ID товара: " product_id
        read -p "Путь к изображению: " image_path
        upload_product_image "$product_id" "$image_path"
        ;;
    *)
        echo -e "${RED}❌ Неверный выбор${NC}"
        exit 1
        ;;
esac

