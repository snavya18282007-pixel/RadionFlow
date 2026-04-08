from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.core.database import get_database_runtime_info, ping_database

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    settings = get_settings()
    database_runtime = get_database_runtime_info()
    return {
        "name": settings.app_name,
        "status": "ok",
        "environment": settings.environment,
        "database": database_runtime["database_url"],
        "database_fallback": database_runtime["fallback_active"],
        "docs": "/docs",
    }


@router.get("/health")
async def health_check():
    settings = get_settings()
    database_runtime = get_database_runtime_info()
    return {
        "status": "ok",
        "environment": settings.environment,
        "database": database_runtime["database_url"],
        "database_fallback": database_runtime["fallback_active"],
    }


@router.get("/health/db")
async def health_db():
    try:
        await ping_database()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
