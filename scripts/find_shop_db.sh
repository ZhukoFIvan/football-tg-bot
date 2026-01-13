#!/bin/bash
# Скрипт для поиска файла shop.db на сервере

echo "🔍 Поиск файла shop.db..."
echo ""

# Поиск в разных местах
SEARCH_PATHS=(
    "/home/deploy/projects/tg-shop"
    "/home/deploy"
    "/tmp"
    "/var/tmp"
    "$HOME"
)

FOUND=0

for path in "${SEARCH_PATHS[@]}"; do
    if [ -f "$path/shop.db" ]; then
        echo "✅ Найден: $path/shop.db"
        ls -lh "$path/shop.db"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "❌ Файл shop.db не найден в стандартных местах"
    echo ""
    echo "💡 Попробуйте найти вручную:"
    echo "   find /home/deploy -name 'shop.db' 2>/dev/null"
    echo ""
    echo "💡 Или скопируйте файл в корень проекта:"
    echo "   cp /путь/к/shop.db /home/deploy/projects/tg-shop/shop.db"
fi
