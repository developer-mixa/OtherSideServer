"""Application settings — single source of truth."""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_KEYS = frozenset({"change-me", "change-me-in-production"})


class Settings(BaseSettings):
    APP_NAME: str = "OtherSide API"
    ENV: str = "local"
    DEBUG: bool = True

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALG: str = "HS256"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800
    CORS_ORIGINS: list[str] = ["*"]

    BOOTSTRAP_ADMIN_USERNAME: str = ""
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    ROBOKASSA_MERCHANT_LOGIN: str = ""
    ROBOKASSA_PASSWORD1: str = ""
    ROBOKASSA_PASSWORD2: str = ""
    ROBOKASSA_IS_TEST: bool = True
    ROBOKASSA_PAYMENT_URL: str = "https://auth.robokassa.ru/Merchant/Index.aspx"

    # Selectel Email Service SMTP relay (or any SMTP-compatible provider) — see README.md
    # "Настройка email-верификации (Selectel)" for the full setup guide.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 1127
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "OtherSide"
    SMTP_USE_TLS: bool = True

    # Public site address, shown in transactional emails.
    SITE_URL: str = "https://otherside-inc.ru"
    EMAIL_VERIFICATION_CODE_TTL_MINUTES: int = 15
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = 5
    # Minimum gap between two verification codes sent to the same address.
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 120

    RATE_LIMIT_AUTH_REQUESTS: int = 10
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = 60
    RATE_LIMIT_CONTACT_REQUESTS: int = 5
    RATE_LIMIT_CONTACT_WINDOW_SECONDS: int = 300
    RATE_LIMIT_WEBHOOK_REQUESTS: int = 100
    RATE_LIMIT_WEBHOOK_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def is_local(self) -> bool:
        return self.ENV.lower() == "local"

    @property
    def bootstrap_admin_configured(self) -> bool:
        return bool(
            self.BOOTSTRAP_ADMIN_USERNAME.strip()
            and self.BOOTSTRAP_ADMIN_EMAIL.strip()
            and self.BOOTSTRAP_ADMIN_PASSWORD
        )

    @model_validator(mode="after")
    def validate_settings(self) -> Settings:
        if self.bootstrap_admin_configured and len(self.BOOTSTRAP_ADMIN_PASSWORD) < 12:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

        if not self.is_production:
            return self

        if self.SECRET_KEY in _INSECURE_SECRET_KEYS:
            raise ValueError("SECRET_KEY must be set to a strong unique value in production")

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")

        if "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must not contain '*' in production")

        if not self.ROBOKASSA_MERCHANT_LOGIN.strip():
            raise ValueError("ROBOKASSA_MERCHANT_LOGIN is required in production")

        if not self.ROBOKASSA_PASSWORD1:
            raise ValueError("ROBOKASSA_PASSWORD1 is required in production")

        if not self.ROBOKASSA_PASSWORD2:
            raise ValueError("ROBOKASSA_PASSWORD2 is required in production")

        if self.ROBOKASSA_IS_TEST:
            raise ValueError("ROBOKASSA_IS_TEST must be false in production")

        if not self.SMTP_HOST.strip():
            raise ValueError("SMTP_HOST is required in production")

        if not self.SMTP_USERNAME.strip():
            raise ValueError("SMTP_USERNAME is required in production")

        if not self.SMTP_PASSWORD:
            raise ValueError("SMTP_PASSWORD is required in production")

        if not self.SMTP_FROM_EMAIL.strip():
            raise ValueError("SMTP_FROM_EMAIL is required in production")

        return self


settings = Settings()
