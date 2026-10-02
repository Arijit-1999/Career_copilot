"""Pytest test fixtures and configuration with in-memory database."""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.common.models import Base
from app.core.database import get_db_session
from app.core.config import Settings
import app.candidate.models  # Register candidate models with Base.metadata
import app.career_profiles.models  # Register career profile models with Base.metadata
import app.jobs.models  # Register job models with Base.metadata
import app.matching.models  # Register matching models with Base.metadata
import app.resumes.models  # Register resumes models with Base.metadata


# In-memory SQLite async engine for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """Creates all database tables before each test and drops them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override for test database session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


fastapi_app.dependency_overrides[get_db_session] = override_get_db_session


@pytest_asyncio.fixture
async def async_client():
    """Yields an async HTTP test client for the FastAPI application."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
