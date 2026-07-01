"""Application settings — single source of truth."""

from __future__ import annotations

from pydantic import model_validator
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

    BOOTSTRAP_ADMIN_USERNAME: str = ""
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    ROBOKASSA_MERCHANT_LOGIN: str = ""
    ROBOKASSA_PASSWORD1: str = ""
    ROBOKASSA_PASSWORD2: str = ""
    ROBOKASSA_IS_TEST: bool = True
    ROBOKASSA_PAYMENT_URL: str = "https://auth.robokassa.ru/Merchant/Index.aspx"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def bootstrap_admin_configured(self) -> bool:
        return bool(
            self.BOOTSTRAP_ADMIN_USERNAME.strip()
            and self.BOOTSTRAP_ADMIN_EMAIL.strip()
            and self.BOOTSTRAP_ADMIN_PASSWORD
        )

    @model_validator(mode="after")
    def validate_bootstrap_credentials(self) -> Settings:
        if not self.bootstrap_admin_configured:
            return self

        if len(self.BOOTSTRAP_ADMIN_PASSWORD) < 12:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

        return self


settings = Settings()
