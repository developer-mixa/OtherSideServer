"""Application settings — single source of truth."""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_KEYS = frozenset({"change-me", "change-me-in-production"})
# HS256 tokens are only as strong as this key: a short/low-entropy value is
# brute-forceable offline from any issued token.
_MIN_SECRET_KEY_LENGTH = 32
# OWASP Password Storage Cheat Sheet minimum for Argon2id.
_MIN_ARGON2_TIME_COST = 2
_MIN_ARGON2_MEMORY_COST_KIB = 19456


class Settings(BaseSettings):
    APP_NAME: str = "OtherSide API"
    ENV: str = "local"
    DEBUG: bool = True

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALG: str = "HS256"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Argon2id parameters. Defaults are the OWASP Password Storage Cheat Sheet baseline
    # (m=19 MiB, t=2, p=1). Raising them later is safe: existing hashes are upgraded on
    # the user's next successful login.
    PASSWORD_HASH_TIME_COST: int = 2
    PASSWORD_HASH_MEMORY_COST_KIB: int = 19456
    PASSWORD_HASH_PARALLELISM: int = 1
    # Hashes computed at once per process; each holds PASSWORD_HASH_MEMORY_COST_KIB of RAM.
    PASSWORD_HASH_MAX_CONCURRENCY: int = 4

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

        if self.REFRESH_TOKEN_EXPIRE_DAYS < 1:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be at least 1")

        if self.PASSWORD_HASH_MAX_CONCURRENCY < 1:
            raise ValueError("PASSWORD_HASH_MAX_CONCURRENCY must be at least 1")

        # Enforce signing-key strength in every environment that is not explicitly
        # local dev. This fails closed: a staging deploy, or a production one whose
        # ENV was left at a non-"production" value, still cannot boot with the
        # publicly-known default or a weak, brute-forceable key.
        if not self.is_local:
            if self.SECRET_KEY in _INSECURE_SECRET_KEYS:
                raise ValueError("SECRET_KEY must be set to a strong unique value outside local")
            if len(self.SECRET_KEY) < _MIN_SECRET_KEY_LENGTH:
                raise ValueError(
                    f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LENGTH} characters outside local"
                )

        if not self.is_production:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")

        # Cheap parameters are fine for tests, never for real user passwords.
        if (
            self.PASSWORD_HASH_TIME_COST < _MIN_ARGON2_TIME_COST
            or self.PASSWORD_HASH_MEMORY_COST_KIB < _MIN_ARGON2_MEMORY_COST_KIB
        ):
            raise ValueError(
                "PASSWORD_HASH_* must be at least the OWASP baseline in production "
                f"(time_cost>={_MIN_ARGON2_TIME_COST}, "
                f"memory_cost_kib>={_MIN_ARGON2_MEMORY_COST_KIB})"
            )

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
