from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    database_url: str = "sqlite:///takeaway.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
