"""Unit tests for configuration settings."""

from app.core.config import Settings


def test_default_settings():
    """Verify default settings initialization."""
    settings = Settings()
    assert settings.app_name == "Career Copilot"
    assert settings.app_env in ["development", "production", "test"]
    assert "postgresql+asyncpg://" in settings.async_database_url
    assert "postgresql://" in settings.sync_database_url


def test_custom_database_url():
    """Verify custom database URL overrides."""
    custom_url = "postgresql+asyncpg://custom_user:custom_pass@custom_host:5432/custom_db"
    settings = Settings(database_url=custom_url)
    assert settings.async_database_url == custom_url
