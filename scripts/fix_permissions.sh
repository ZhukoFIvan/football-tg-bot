#!/bin/bash

echo "🔧 Fixing permissions..."

# Создать директории если не существуют
mkdir -p uploads/sections
mkdir -p uploads/categories
mkdir -p uploads/products
mkdir -p uploads/banners

# Установить правильные права
sudo chown -R $USER:$USER uploads/
chmod -R 755 uploads/

echo "✅ Permissions fixed!"
