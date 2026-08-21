from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # === ROOT PATH ===
    root_path: str = "/api/v1/proxy-finance"
    http_port: int = 8000

    # === IDENTIFICACAO DE BANCO ===
    logo_hash_threshold: int = 10
    poppler_path: str = ""

    # === AUTENTICACAO ===
    api_key: str = ""
    api_key_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
