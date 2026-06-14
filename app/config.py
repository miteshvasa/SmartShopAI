from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartShopAI"
    environment: str = "local"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    database_url: str = "sqlite+aiosqlite:///./smartshop.db"
    allowed_origins: str = "http://localhost:8501"
    enable_ephemeral_memory: bool = True
    memory_ttl_seconds: int = 1800
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
