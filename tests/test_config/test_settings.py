"""Settings validation tests."""

import pytest
from pydantic import ValidationError

from config.settings import Settings


class TestProductionSettingsValidation:
    def test_production_requires_strong_secret(self) -> None:
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(
                ENV="production",
                DEBUG=False,
                SECRET_KEY="change-me",
                CORS_ORIGINS=["https://example.com"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=False,
            )

    def test_production_rejects_test_robokassa(self) -> None:
        with pytest.raises(ValidationError, match="ROBOKASSA_IS_TEST"):
            Settings(
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key",
                CORS_ORIGINS=["https://example.com"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=True,
            )

    def test_production_rejects_wildcard_cors(self) -> None:
        with pytest.raises(ValidationError, match="CORS_ORIGINS"):
            Settings(
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key",
                CORS_ORIGINS=["*"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=False,
            )

    def test_production_requires_smtp_host(self) -> None:
        with pytest.raises(ValidationError, match="SMTP_HOST"):
            Settings(
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key",
                CORS_ORIGINS=["https://example.com"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=False,
            )

    def test_production_allows_full_smtp_config(self) -> None:
        settings = Settings(
            ENV="production",
            DEBUG=False,
            SECRET_KEY="super-secret-production-key",
            CORS_ORIGINS=["https://example.com"],
            ROBOKASSA_MERCHANT_LOGIN="shop",
            ROBOKASSA_PASSWORD1="pass1",
            ROBOKASSA_PASSWORD2="pass2",
            ROBOKASSA_IS_TEST=False,
            SMTP_HOST="smtp.mail.selcloud.ru",
            SMTP_USERNAME="user",
            SMTP_PASSWORD="secret",
            SMTP_FROM_EMAIL="noreply@otherside-inc.ru",
        )
        assert settings.is_production is True

    def test_local_allows_defaults(self) -> None:
        settings = Settings(
            _env_file=None,
            ENV="local",
            SECRET_KEY="change-me",
        )
        assert settings.is_local is True
        assert settings.SECRET_KEY == "change-me"
