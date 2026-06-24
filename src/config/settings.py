"""Application settings — single source of truth."""

from uuid import UUID

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OtherSide API"
    ENV: str = "local"
    DEBUG: bool = True

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALG: str = "HS256"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    CORS_ORIGINS: list[str] = ["*"]
    ADMIN_ROLE_IDS: list[str] = []

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("ADMIN_ROLE_IDS", mode="before")
    @classmethod
    def _parse_admin_role_ids(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item) for item in value]
        return []


settings = Settings()


def is_admin_role(role_id: UUID | None) -> bool:
    """Check whether role_id belongs to configured admin roles."""
    if role_id is None or not settings.ADMIN_ROLE_IDS:
        return False
    return str(role_id) in settings.ADMIN_ROLE_IDS
