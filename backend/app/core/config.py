from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    database_url: str
    app_name:str= "Lamaplast ABC"
    app_env: str = "development"  # Options: development, production, testing
    cors_origins: list[str] = ["*"] 

    secret_key: str  
    session_hours: int = 8
    cookie_secure: bool = True
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    min_password_length: int = 12

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
