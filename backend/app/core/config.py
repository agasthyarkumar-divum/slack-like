"""
Central, env-driven application config (architecture.md §4).

Every place in the codebase that needs the product name, a secret, or a backend
selector (STORAGE_BACKEND, DATABASE_URL, ...) reads it from `settings` here rather
than hardcoding it — this is the single file that changes when deploying a
differently-branded or differently-configured instance.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App identity ---
    APP_NAME: str = "Company Chat"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development | staging | production

    # Generic company-facing identifiers, kept out of code/identifiers elsewhere
    # and sourced only from here (see kickoff note: no hardcoded product-name
    # strings scattered through the codebase).
    COMPANY_NAME: str = "Company"
    COMPANY_SLACK_NAME: str = "Company Chat"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://company_chat:company_chat@localhost:5432/company_chat"
    )

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Auth / JWT (architecture.md §7) ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- File storage (StorageBackend, architecture.md §2) ---
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_STORAGE_PATH: str = "/srv/company-chat/uploads"
    FILE_ENCRYPTION_KEY: str = ""  # Fernet key; required once storage/local.py lands

    # --- Files pipeline (architecture.md §8) ---
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB
    THUMBNAIL_MAX_DIMENSION: int = 512

    # --- S3 (unused while STORAGE_BACKEND=local) ---
    S3_BUCKET: str | None = None
    S3_REGION: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None

    # --- Push notifications (architecture.md §9, stubbed until Phase 9) ---
    FCM_SERVER_KEY: str | None = None
    FCM_CREDENTIALS_JSON_PATH: str | None = None

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
