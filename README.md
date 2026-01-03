# 🎮 Telegram Game Keys Shop

Production-ready backend для магазина игровых ключей в Telegram Mini App.

## 📋 Содержание

- [Стек технологий](#стек-технологий)
- [Структура проекта](#структура-проекта)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [База данных](#база-данных)
- [API Endpoints](#api-endpoints)
- [Административная панель](#административная-панель)
- [Telegram Bot](#telegram-bot)
- [Авторизация](#авторизация)
- [Разработка](#разработка)
- [Деплой второго бота](#деплой-второго-бота)
- [Troubleshooting](#troubleshooting)

---

## 🛠 Стек технологий

- **Python 3.11+**
- **FastAPI** - REST API фреймворк
- **PostgreSQL** - основная база данных
- **SQLAlchemy 2.0** - async ORM
- **Alembic** - миграции БД
- **aiogram 3.x** - Telegram Bot framework
- **Docker & Docker Compose** - контейнеризация
- **pydantic-settings** - управление конфигурацией

---

## 📁 Структура проекта

```
project/
├── apps/
│   ├── api/                    # FastAPI приложение
│   │   ├── main.py            # Точка входа API
│   │   └── routes/            # API роуты
│   │       ├── health.py      # Health check
│   │       ├── public.py      # Публичные эндпоинты (каталог)
│   │       └── auth.py        # Авторизация через Telegram
│   └── bot/                   # Telegram Bot
│       ├── main.py            # Точка входа бота
│       └── handlers/          # Обработчики команд
│           └── start.py       # /start команда
├── core/
│   ├── config.py              # Конфигурация (pydantic-settings)
│   ├── auth.py                # JWT и проверка Telegram initData
│   ├── db/                    # База данных
│   │   ├── base.py           # SQLAlchemy Base
│   │   ├── session.py        # Async session management
│   │   └── models.py         # Модели БД
│   ├── payments/             # 🔜 Placeholder для платежей
│   └── services/             # 🔜 Placeholder для бизнес-логики
├── alembic/                   # Миграции БД
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example              # Пример конфигурации
├── .gitignore
└── README.md
```

---

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
# Перейдите в директорию проекта
cd tg-web-app-ecomm

# Создайте .env файл из примера
cp .env.example .env

# Отредактируйте .env - ОБЯЗАТЕЛЬНО укажите:
# - BOT_TOKEN (получите у @BotFather)
# - TG_WEBAPP_BOT_TOKEN (обычно = BOT_TOKEN)
# - JWT_SECRET (случайная строка)
# - OWNER_TG_IDS (ваш Telegram ID)
nano .env
```

### 2. Запуск через Docker Compose

```bash
# Поднять все сервисы (postgres, api, bot)
docker compose up -d --build

# Проверить статус
docker compose ps

# Просмотр логов
docker compose logs -f api
docker compose logs -f bot
```

### 3. Применение миграций БД

```bash
# Выполнить миграции внутри контейнера API
docker compose exec api alembic upgrade head

# Проверить текущую версию БД
docker compose exec api alembic current
```

### 4. Проверка работоспособности

```bash
# Health check API
curl http://localhost:8000/health

# Должен вернуть: {"status":"ok"}

# Проверка документации API
open http://localhost:8000/docs
```

### 5. Тестирование бота

Откройте Telegram и найдите вашего бота, отправьте `/start`.

---

## ⚙️ Конфигурация

Все настройки управляются через `.env` файл. Основные переменные:

### База данных

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/tg_shop
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=tg_shop
```

### Telegram Bot

```env
# Получите токен у @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TG_WEBAPP_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Безопасность

```env
# Сгенерируйте: openssl rand -hex 32
JWT_SECRET=your-super-secret-jwt-key-change-me-in-production

# Сгенерируйте: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-32-char-encryption-key-here
```

### Администраторы

```env
# Узнайте свой ID у @userinfobot
OWNER_TG_IDS=123456789,987654321
```

### API

```env
API_PUBLIC_URL=http://localhost:8000
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

---

## 🗄 База данных

### Модели

#### Users (Пользователи)
- `id` - первичный ключ
- `telegram_id` - уникальный ID из Telegram
- `username` - username пользователя
- `first_name`, `last_name` - имя и фамилия
- `is_banned` - флаг бана
- `created_at`, `updated_at` - временные метки

#### Sections (Разделы каталога)
- `id` - первичный ключ
- `title` - название раздела
- `slug` - уникальный URL-friendly идентификатор
- `sort_order` - порядок сортировки
- `is_active` - активность раздела

#### Categories (Категории)
- `id` - первичный ключ
- `section_id` - FK на sections
- `title` - название категории
- `slug` - URL-friendly идентификатор
- `sort_order` - порядок сортировки
- `is_active` - активность категории

#### Products (Товары/Игровые ключи)
- `id` - первичный ключ
- `category_id` - FK на categories
- `title` - название товара
- `slug` - URL-friendly идентификатор
- `description` - описание товара
- `image` - URL изображения товара
- `price` - текущая цена (Numeric)
- `old_price` - старая цена для отображения скидки
- `currency` - валюта (по умолчанию RUB)
- `stock_count` - количество на складе
- `is_active` - активность товара
- `created_at`, `updated_at` - временные метки

#### Cart (Корзина)
- `id` - первичный ключ
- `user_id` - FK на users (уникальный, один пользователь = одна корзина)
- `created_at`, `updated_at` - временные метки

#### CartItem (Товар в корзине)
- `id` - первичный ключ
- `cart_id` - FK на carts
- `product_id` - FK на products
- `quantity` - количество товара
- `created_at`, `updated_at` - временные метки

#### Order (Заказ)
- `id` - первичный ключ
- `user_id` - FK на users
- `status` - статус заказа (pending/paid/completed/cancelled)
- `total_amount` - общая сумма заказа
- `currency` - валюта
- `created_at`, `updated_at` - временные метки

#### OrderItem (Товар в заказе)
- `id` - первичный ключ
- `order_id` - FK на orders
- `product_id` - FK на products (может быть NULL)
- `product_title` - название товара на момент покупки
- `quantity` - количество
- `price` - цена на момент покупки
- `created_at` - временная метка

#### Badge (Бейдж для товаров)
- `id` - первичный ключ
- `title` - текст бейджа ("Скидка 20%", "Новинка")
- `color` - цвет фона (HEX)
- `text_color` - цвет текста (HEX)
- `is_active` - активность
- `created_at` - временная метка

#### Banner (Баннер для главной)
- `id` - первичный ключ
- `title` - заголовок баннера
- `description` - описание
- `image` - URL изображения
- `link` - ссылка при клике
- `sort_order` - порядок отображения
- `is_active` - активность
- `created_at` - временная метка

### Работа с миграциями

```bash
# Применить все миграции
docker compose exec api alembic upgrade head

# Откатить последнюю миграцию
docker compose exec api alembic downgrade -1

# Создать новую миграцию (автогенерация)
docker compose exec api alembic revision --autogenerate -m "Description"

# Посмотреть текущую версию
docker compose exec api alembic current

# История миграций
docker compose exec api alembic history
```

### Добавление тестовых данных

**Автоматическое заполнение (рекомендуется):**

```bash
# Запустить скрипт заполнения базы моковыми данными
docker compose exec api python scripts/seed_data.py
```

Скрипт создаст:
- ✅ 2 пользователя (1 admin с Telegram ID: 123456789)
- ✅ 7 бейджей (Скидка 20%, Новинка, Хит продаж и т.д.)
- ✅ 3 баннера для главной страницы
- ✅ 3 раздела (PC Games, Console Games, Gift Cards)
- ✅ 11 категорий (Action, RPG, Strategy, PlayStation, Xbox и т.д.)
- ✅ 15+ товаров с ценами, описаниями и бейджами

**Ручное добавление через SQL:**

```bash
# Подключитесь к PostgreSQL
docker compose exec postgres psql -U postgres -d tg_shop

# Пример SQL для добавления данных:
INSERT INTO sections (title, slug, sort_order, is_active) 
VALUES ('PC Games', 'pc-games', 1, true);

INSERT INTO categories (section_id, title, slug, sort_order, is_active) 
VALUES (1, 'Action', 'action', 1, true);

INSERT INTO products (category_id, title, slug, description, price, currency, stock_count, is_active)
VALUES (1, 'Cyberpunk 2077', 'cyberpunk-2077', 'Futuristic RPG game', 1999.00, 'RUB', 10, true);
```

---

## 🌐 API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

### Авторизация

```http
POST /auth/telegram
Content-Type: application/json

{
  "initData": "query_id=...&user=...&hash=..."
}
```

**Response:**
```json
{
  "ok": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": 1,
  "telegram_id": 123456789
}
```

### Публичные эндпоинты

#### Получить разделы

```http
GET /public/sections
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "PC Games",
    "slug": "pc-games",
    "sort_order": 1,
    "is_active": true
  }
]
```

#### Получить категории

```http
GET /public/categories?section_id=1
```

**Response:**
```json
[
  {
    "id": 1,
    "section_id": 1,
    "title": "Action",
    "slug": "action",
    "sort_order": 1,
    "is_active": true
  }
]
```

#### Получить товары

```http
GET /public/products?category_id=1&limit=10&offset=0
```

**Response:**
```json
[
  {
    "id": 1,
    "category_id": 1,
    "title": "Cyberpunk 2077",
    "slug": "cyberpunk-2077",
    "description": "Futuristic RPG game",
    "price": 1999.00,
    "currency": "RUB",
    "stock_count": 10,
    "is_active": true
  }
]
```

#### Получить товар по ID

```http
GET /public/products/1
```

**Response:**
```json
{
  "id": 1,
  "category_id": 1,
  "title": "Cyberpunk 2077",
  "slug": "cyberpunk-2077",
  "description": "Futuristic RPG game",
  "price": 1999.00,
  "currency": "RUB",
  "stock_count": 10,
  "is_active": true
}
```

#### Получить баннеры

```http
GET /public/banners
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Новогодняя распродажа",
    "description": "Скидки до 50%",
    "image": "/uploads/banners/banner-123.jpg",
    "link": "/category/action",
    "sort_order": 1
  }
]
```

#### Получить бейджи

```http
GET /public/badges
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Скидка 20%",
    "color": "#FF5722",
    "text_color": "#FFFFFF"
  }
]
```

### Swagger документация

Интерактивная документация доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🛒 Корзина и заказы

### Корзина пользователя

Каждый пользователь имеет свою персональную корзину, которая сохраняется между сессиями.

#### Работа с корзиной

```http
GET    /cart              # Получить корзину
POST   /cart/items        # Добавить товар
PATCH  /cart/items/{id}   # Изменить количество
DELETE /cart/items/{id}   # Удалить товар
DELETE /cart              # Очистить корзину
```

**Пример добавления товара в корзину:**

```bash
curl -X POST "http://localhost:8000/cart/items" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }'
```

**Ответ:**

```json
{
  "id": 1,
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_title": "Cyberpunk 2077",
      "product_image": "/uploads/products/abc.jpg",
      "product_price": 1999.00,
      "product_old_price": 2999.00,
      "quantity": 2,
      "subtotal": 3998.00
    }
  ],
  "total_items": 2,
  "total_amount": 3998.00
}
```

### Заказы

После оформления заказа корзина автоматически очищается, товары резервируются на складе.

#### Работа с заказами

```http
GET    /orders              # Список моих заказов
GET    /orders/{id}         # Детали заказа
POST   /orders              # Создать заказ из корзины
POST   /orders/{id}/cancel  # Отменить заказ
```

**Создание заказа из корзины:**

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Ответ:**

```json
{
  "id": 1,
  "status": "pending",
  "total_amount": 3998.00,
  "currency": "RUB",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_title": "Cyberpunk 2077",
      "quantity": 2,
      "price": 1999.00
    }
  ],
  "created_at": "2025-12-19T18:30:00"
}
```

### Статусы заказов

- **pending** - ожидает оплаты
- **paid** - оплачен
- **completed** - выполнен (ключи выданы)
- **cancelled** - отменен

### Логика работы

1. **Добавление в корзину:**
   - Если товар уже есть → увеличивается количество
   - Если товара нет → добавляется новый

2. **Оформление заказа:**
   - Проверяется наличие товаров на складе
   - Создается заказ со статусом "pending"
   - Товары резервируются (уменьшается stock_count)
   - Корзина очищается автоматически

3. **Отмена заказа:**
   - Можно отменить только заказы со статусом "pending"
   - Товары возвращаются на склад

---

## 🔐 Административная панель

### Обзор возможностей

Административная панель предоставляет полный контроль над контентом магазина:

- ✅ **Управление разделами** - создание, редактирование, загрузка фоновых изображений и иконок
- ✅ **Управление категориями** - организация товаров по категориям с изображениями
- ✅ **Управление товарами** - добавление игровых ключей с ценами, описаниями, скидками
- ✅ **Управление бейджами** - создание меток для товаров (Скидка 20%, Новинка, Хит продаж)
- ✅ **Управление баннерами** - слайдер на главной странице
- ✅ **Детальная статистика** - пользователи, заказы, выручка, топ товаров

### Как стать администратором

**Способ 1: Через OWNER_TG_IDS (рекомендуется)**

Добавьте свой Telegram ID в `.env`:

```env
OWNER_TG_IDS=123456789,987654321
```

При первой авторизации через `/auth/telegram` автоматически установится флаг `is_admin`.

**Способ 2: Через базу данных**

```sql
UPDATE users SET is_admin = true WHERE telegram_id = 123456789;
```

### Основные эндпоинты

Все административные эндпоинты требуют JWT токен в заголовке:

```http
Authorization: Bearer <jwt_token>
```

#### Управление разделами

```http
GET    /admin/sections              # Получить все разделы
POST   /admin/sections              # Создать раздел
PATCH  /admin/sections/{id}         # Обновить раздел
DELETE /admin/sections/{id}         # Удалить раздел
POST   /admin/sections/{id}/background  # Загрузить фон
POST   /admin/sections/{id}/icon    # Загрузить иконку
```

#### Управление категориями

```http
GET    /admin/categories            # Получить все категории
POST   /admin/categories            # Создать категорию
PATCH  /admin/categories/{id}       # Обновить категорию
DELETE /admin/categories/{id}       # Удалить категорию
POST   /admin/categories/{id}/image # Загрузить изображение
```

#### Управление товарами

```http
GET    /admin/products              # Получить все товары
GET    /admin/products/{id}         # Получить один товар по ID
POST   /admin/products              # Создать товар
PATCH  /admin/products/{id}         # Обновить товар
DELETE /admin/products/{id}         # Удалить товар
POST   /admin/products/{id}/images  # Загрузить изображения
```

#### Управление бейджами

```http
GET    /admin/badges                # Получить все бейджи
POST   /admin/badges                # Создать бейдж
PATCH  /admin/badges/{id}           # Обновить бейдж
DELETE /admin/badges/{id}           # Удалить бейдж
```

#### Управление баннерами

```http
GET    /admin/banners               # Получить все баннеры
POST   /admin/banners               # Создать баннер
PATCH  /admin/banners/{id}          # Обновить баннер
DELETE /admin/banners/{id}          # Удалить баннер
POST   /admin/banners/{id}/image    # Загрузить изображение
```

#### Статистика

```http
GET /admin/stats/overview           # Общая статистика
GET /admin/stats/users              # Статистика пользователей
GET /admin/stats/orders             # Статистика заказов
GET /admin/stats/revenue            # Статистика выручки
GET /admin/stats/products           # Статистика товаров
GET /admin/stats/top-products       # Топ товаров по продажам
GET /admin/stats/recent-users       # Последние пользователи
GET /admin/stats/recent-orders      # Последние заказы
```

### Пример создания товара

```bash
# 1. Создать товар
curl -X POST "http://localhost:8000/admin/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 1,
    "title": "Cyberpunk 2077",
    "slug": "cyberpunk-2077",
    "description": "Futuristic RPG game",
    "price": 1999.00,
    "old_price": 2999.00,
    "stock_count": 10,
    "badge_ids": [1, 2]
  }'

# 2. Загрузить изображение
curl -X POST "http://localhost:8000/admin/products/1/image" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@cyberpunk.jpg"
```

### Полная документация

Подробная документация по административной панели: **[ADMIN_DOCS.md](ADMIN_DOCS.md)**

---

## 🤖 Telegram Bot

### Команды

- `/start` - Приветственное сообщение

### Расширение функционала

Добавление новых команд в `apps/bot/handlers/`:

```python
# apps/bot/handlers/catalog.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    await message.answer("Каталог товаров...")
```

Регистрация в `apps/bot/main.py`:

```python
from apps.bot.handlers import start, catalog

dp.include_router(start.router)
dp.include_router(catalog.router)
```

---

## 🔐 Авторизация

### Как работает авторизация

1. **Telegram Mini App** отправляет `initData` на `/auth/telegram`
2. **Backend** проверяет подпись `initData` используя `TG_WEBAPP_BOT_TOKEN`
3. Если валидно - создается/обновляется пользователь в БД
4. Генерируется **JWT токен** со сроком действия 30 дней
5. Токен возвращается клиенту

### Использование JWT токена

В последующих запросах передавайте токен в заголовке:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Проверка токена (пример middleware)

```python
from fastapi import Depends, HTTPException, Header
from core.auth import verify_jwt_token

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload
```

---

## 💻 Разработка

### Локальная разработка без Docker

```bash
# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить PostgreSQL отдельно или использовать только postgres из compose
docker compose up -d postgres

# Обновить DATABASE_URL в .env для локального подключения
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tg_shop

# Применить миграции
alembic upgrade head

# Запустить API
python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# В другом терминале запустить бота
python -m apps.bot.main
```

### Создание новой миграции

```bash
# После изменения моделей в core/db/models.py
docker compose exec api alembic revision --autogenerate -m "Add new field to products"

# Проверить сгенерированную миграцию
cat alembic/versions/002_add_new_field_to_products.py

# Применить
docker compose exec api alembic upgrade head
```

### Полезные команды Docker

```bash
# Остановить все сервисы
docker compose down

# Остановить и удалить volumes (БД будет очищена!)
docker compose down -v

# Пересобрать образы
docker compose build --no-cache

# Перезапустить конкретный сервис
docker compose restart api

# Посмотреть логи в реальном времени
docker compose logs -f

# Выполнить команду в контейнере
docker compose exec api bash
docker compose exec postgres psql -U postgres -d tg_shop

# Посмотреть использование ресурсов
docker compose stats
```

---

## 🔄 Деплой второго бота

Проект спроектирован так, чтобы легко разворачивать несколько независимых ботов.

### Вариант 1: На том же сервере (разные порты)

```bash
# Скопировать проект в другую директорию
cp -r tg-web-app-ecomm tg-web-app-ecomm-bot2
cd tg-web-app-ecomm-bot2

# Создать новый .env с другими настройками
cp .env.example .env
nano .env

# Изменить:
# - BOT_TOKEN (новый токен от @BotFather)
# - DATABASE_URL (новая БД или другой хост)
# - API_PORT=8001 (другой порт)
# - POSTGRES_DB=tg_shop_bot2

# Запустить
docker compose up -d --build
docker compose exec api alembic upgrade head
```

### Вариант 2: На другом сервере

```bash
# На новом сервере
git clone <your-repo>
cd tg-web-app-ecomm

# Настроить .env с новыми credentials
cp .env.example .env
nano .env

# Запустить
docker compose up -d --build
docker compose exec api alembic upgrade head
```

### Важно при деплое второго бота

- ✅ Каждый бот должен иметь **свой BOT_TOKEN**
- ✅ Каждый бот должен использовать **свою БД** (или разные схемы)
- ✅ Если на одном сервере - **разные порты** для API
- ✅ **Разные OWNER_TG_IDS** если разные владельцы
- ✅ **Разные JWT_SECRET** для безопасности

---

## 🐛 Troubleshooting

### API не запускается

```bash
# Проверить логи
docker compose logs api

# Частые причины:
# 1. Порт 8000 занят - измените API_PORT в .env
# 2. Неверный DATABASE_URL
# 3. PostgreSQL не готов - подождите ~10 секунд
```

### Bot не запускается

```bash
# Проверить логи
docker compose logs bot

# Частые причины:
# 1. Неверный BOT_TOKEN
# 2. Токен уже используется другим процессом
# 3. Нет доступа к Telegram API (firewall)
```

### Ошибки миграций

```bash
# Проверить текущую версию
docker compose exec api alembic current

# Если БД не синхронизирована
docker compose exec api alembic stamp head

# Если нужно пересоздать БД
docker compose down -v
docker compose up -d
docker compose exec api alembic upgrade head
```

### PostgreSQL проблемы

```bash
# Подключиться к БД
docker compose exec postgres psql -U postgres -d tg_shop

# Посмотреть таблицы
\dt

# Посмотреть структуру таблицы
\d users

# Выйти
\q
```

### Авторизация не работает

1. Проверьте что `TG_WEBAPP_BOT_TOKEN` совпадает с `BOT_TOKEN`
2. Убедитесь что `initData` передается корректно из Mini App
3. Проверьте что `JWT_SECRET` установлен

### Проверка здоровья системы

```bash
# API health check
curl http://localhost:8000/health

# Проверка БД
docker compose exec postgres pg_isready -U postgres

# Проверка всех контейнеров
docker compose ps
```

---

## 📚 Дополнительные ресурсы

### Документация

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [aiogram 3.x](https://docs.aiogram.dev/en/latest/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Mini Apps](https://core.telegram.org/bots/webapps)

### Полезные команды для разработки

```bash
# Форматирование кода (если установлен black)
black apps/ core/

# Линтинг (если установлен ruff)
ruff check apps/ core/

# Тесты (если настроены)
pytest

# Экспорт зависимостей
pip freeze > requirements.txt
```

---

## 📝 TODO / Roadmap

- [ ] Интеграция платежей (Telegram Stars, ЮKassa, Stripe)
- [ ] Админ-панель для управления товарами
- [ ] Система заказов и истории покупок
- [ ] Шифрование и выдача игровых ключей
- [ ] Уведомления о новых товарах
- [ ] Система скидок и промокодов
- [ ] Webhook режим для бота (вместо polling)
- [ ] CI/CD pipeline
- [ ] Мониторинг и логирование (Sentry, Prometheus)
- [ ] Тесты (pytest)

---

## 📄 Лицензия

MIT License - используйте как хотите!

---

## 🤝 Поддержка

Если возникли вопросы или проблемы:

1. Проверьте раздел [Troubleshooting](#troubleshooting)
2. Посмотрите логи: `docker compose logs -f`
3. Проверьте конфигурацию в `.env`

---

**Удачи в разработке! 🚀**
