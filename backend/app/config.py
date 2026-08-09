from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@postgres:5432/docprocessing"
    sync_database_url: str = "postgresql://user:password@postgres:5432/docprocessing"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    openai_api_key: str = ""
    upload_dir: str = "/app/uploads"
    max_file_size_mb: int = 20
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@docprocessing.app"
    # Documents whose heuristic extraction-confidence score falls below this
    # threshold (0-100) are flagged needs_review instead of completed.
    confidence_threshold: int = 60

    _DEFAULT_SECRET_KEY = "change-me-in-production-use-long-random-string"

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def _reject_default_secret_key(self) -> "Settings":
        if self.secret_key == self._DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is still set to the insecure default value. Set "
                "SECRET_KEY in your environment or .env to a long random string "
                "before starting the service."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
