"""Unit tests for database connection and health check."""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.database import check_database_health


@pytest.mark.asyncio
async def test_database_health_check_handles_disconnection():
    """Verify check_database_health returns disconnected status when DB is unreachable."""
    with patch("sqlalchemy.ext.asyncio.AsyncEngine.connect", side_effect=Exception("Connection refused")):
        health = await check_database_health()
        assert health["status"] == "unhealthy"
        assert health["database"] == "disconnected"
        assert "Connection refused" in health["error"]
