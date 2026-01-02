"""
FastAPI приложение - REST API для Telegram Mini App
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from core.config import settings

# Импорт роутеров
from apps.api.routes import health, public, auth, admin, stats, public_banners, cart, orders, bonus, admin_bonus, admin_cleanup, reviews, promo_codes

# Создание приложения
app = FastAPI(
    title="Telegram Game Keys Shop API",
    description="REST API для магазина игровых ключей в Telegram",
    version="1.0.0",
    debug=settings.DEBUG,
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
    openapi_url="/api/openapi.json"  # OpenAPI схема
)

# CORS middleware для Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене можно ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы для загруженных изображений
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Подключение роутеров с префиксом /api
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(public.router, prefix="/api", tags=["Catalog"])
app.include_router(public_banners.router, prefix="/api",
                   tags=["Banners & Badges"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(bonus.router, prefix="/api/bonus", tags=["Bonus"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_bonus.router,
                   prefix="/api/admin/bonus", tags=["Admin Bonus"])
app.include_router(stats.router, prefix="/api/admin/stats",
                   tags=["Admin Stats"])
app.include_router(admin_cleanup.router, prefix="/api/admin",
                   tags=["Admin Cleanup"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(promo_codes.router, prefix="/api", tags=["Promo Codes"])


@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    import logging
    import asyncio
    from core.tasks import run_cleanup_task

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logging.info("🚀 API Server starting...")
    logging.info(f"📍 API URL: {settings.API_PUBLIC_URL}")

    # Запустить фоновую задачу очистки просроченных секций
    asyncio.create_task(run_cleanup_task())
    logging.info("✅ Background cleanup task started")


@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения"""
    print("🛑 API Server shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
