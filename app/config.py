from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_dsn: str = (
        "postgresql+asyncpg://documents:documents@localhost:5432/documents"
    )
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "documents"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
