#!/usr/bin/env bash
# Запуск на сервере из каталога с docker-compose.yml и .env
set -euo pipefail

echo "=== 1) Контейнеры ==="
(docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null) || true

echo ""
echo "=== 2) Последние строки лога API (ошибки старта / traceback) ==="
(docker compose logs api --tail=120 2>/dev/null || docker-compose logs api --tail=120 2>/dev/null) || true

echo ""
echo "=== 3) Локальный health (nginx проксирует сюда) ==="
curl -sS -m 5 -w "\nHTTP:%{http_code}\n" http://127.0.0.1:8000/api/health || echo "curl: upstream недоступен (connection refused / timeout)"

echo ""
echo "=== 4) Nginx error.log (если есть права) ==="
sudo tail -40 /var/log/nginx/error.log 2>/dev/null || echo "(нет sudo или другой путь к логу)"

echo ""
echo "Если API падает при старте: см. traceback в п.2. Часто — неверный .env, БД недоступна, SyntaxError после деплоя."
echo "После правок кода: docker compose build api && docker compose up -d api"
