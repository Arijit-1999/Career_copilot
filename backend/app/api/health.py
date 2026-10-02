"""Health check and readiness endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.database import check_database_health

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic service liveness check."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "debug": settings.app_debug
    }


@router.get("/health/db")
async def database_health_check():
    """Database connectivity and pgvector readiness check."""
    db_status = await check_database_health()
    status_code = status.HTTP_200_OK if db_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=db_status)
