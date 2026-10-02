"""Database engine, session factory, and connection utilities."""

from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.app_debug,
    future=True,
    pool_pre_ping=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> Dict[str, Any]:
    """Verifies connection to PostgreSQL and checks pgvector availability."""
    result = {
        "status": "unhealthy",
        "database": "disconnected",
        "pgvector": "unavailable",
        "version": None,
        "error": None
    }
    try:
        async with engine.connect() as conn:
            # Check basic connection and PostgreSQL version
            version_res = await conn.execute(text("SELECT version();"))
            db_version = version_res.scalar()
            result["database"] = "connected"
            result["version"] = db_version

            # Check pgvector extension
            vector_res = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            )
            has_vector = vector_res.scalar()
            if has_vector:
                result["pgvector"] = "available"
            else:
                result["pgvector"] = "not_installed"

            result["status"] = "healthy"
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        result["error"] = str(exc)

    return result
