"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # App
    app_name: str = "Career Copilot"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change-this-to-a-secure-random-secret-key-for-production"

    # Database
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "career_copilot"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None
    database_url_sync: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    # LLM Providers (Groq, Gemini, Ollama, OpenRouter, OpenAI, Anthropic, Custom vLLM)
    default_llm_provider: str = "groq"
    
    # Groq (Ultra-Fast Open Source Models: LLaMA-3.3, Mixtral, DeepSeek)
    groq_api_key: Optional[str] = None
    groq_default_model: str = "llama-3.3-70b-versatile"
    
    # Google Gemini
    gemini_api_key: Optional[str] = None
    gemini_default_model: str = "gemini-2.5-flash"
    
    # Ollama (Local Private Models)
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    
    # OpenRouter (Universal Multi-Model Gateway)
    openrouter_api_key: Optional[str] = None
    openrouter_default_model: str = "meta-llama/llama-3.3-70b-instruct"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_default_model: str = "gpt-4o-mini"
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_default_model: str = "claude-3-5-sonnet-20241022"

    # Custom OpenAI-Compatible Base URL (vLLM, LMStudio, LocalAI, Text-Gen-WebUI)
    custom_llm_base_url: Optional[str] = None
    custom_llm_api_key: Optional[str] = None
    custom_llm_model: Optional[str] = "local-model"

    @property
    def async_database_url(self) -> str:
        """Returns the async SQLAlchemy database URL."""
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def sync_database_url(self) -> str:
        """Returns the synchronous database URL (useful for Alembic migrations)."""
        if self.database_url_sync:
            return self.database_url_sync
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache()
def get_settings() -> Settings:
    """Returns cached settings instance."""
    return Settings()
