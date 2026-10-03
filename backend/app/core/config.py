from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    database_url: str
    app_name:str= "Lamaplast ABC"
    app_env: str = "development"  # Options: development, production, testing
    cors_origins: list[str] = ["*"]  # List of allowed CORS origins

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()