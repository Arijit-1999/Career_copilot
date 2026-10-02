"""Integration tests for health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Verify basic service liveness check returns 200 and expected payload."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify root index endpoint serves the dashboard."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "Career Copilot" in response.text
