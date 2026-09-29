from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./vireo.db"
    ai_provider: str = "mock"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    ai_max_concurrency: int = Field(default=8, ge=1, le=64)
    ai_max_retries: int = Field(default=3, ge=0, le=8)
    classification_batch_size: int = Field(default=25, ge=1, le=500)
    data_dir: str = "./data"
    analysis_start: str = "2025-01-01"
    analysis_end: str = "2026-06-30"
    cors_origins: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
