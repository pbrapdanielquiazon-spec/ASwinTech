# app/config.py
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# If your .env is at Backend/.env (one level up from /app)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

class Settings(BaseSettings):
    # ---- Your env vars (add what you actually use) ----
    
    ADMIN_SIGNUP_CODE: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120 
    
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "piggery_db"
    DB_USER: str = "root"
    DB_PASSWORD: str | None = None

    RESEND_API_KEY: str
    APP_SECRET: str = "super_long_random_secret"

    OTP_CODE_LENGTH: int = 6
    OTP_EXP_MINUTES: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 3

    # Tell Pydantic where the .env lives
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

@lru_cache
def get_settings() -> "Settings":
    return Settings()

# convenient singleton
settings = get_settings()
