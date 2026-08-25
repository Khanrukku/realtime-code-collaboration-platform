from fastapi import FastAPI

from app.api.routes import router as api_router
from app.api.websocket import router as ws_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)

@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
