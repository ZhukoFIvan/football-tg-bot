"""
FastAPI приложение - REST API для Telegram Mini App
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from core.config import settings

# Импорт роутеров
from apps.api.routes import health, public, auth, admin, stats, public_banners, cart, orders

# Создание приложения
app = FastAPI(
    title="Telegram Game Keys Shop API",
    description="REST API для магазина игровых ключей в Telegram",
    version="1.0.0",
    debug=settings.DEBUG,
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

# Подключение роутеров
app.include_router(health.router, tags=["Health"])
app.include_router(public.router, prefix="/public", tags=["Public"])
app.include_router(public_banners.router, prefix="/public", tags=["Public"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(stats.router, prefix="/admin/stats", tags=["Admin Stats"])


@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    print("🚀 API Server starting...")
    print(f"📍 API URL: {settings.API_PUBLIC_URL}")


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
