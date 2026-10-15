"""Settings validation tests."""

import pytest
from pydantic import ValidationError

from config.settings import Settings


class TestProductionSettingsValidation:
    def test_production_requires_strong_secret(self) -> None:
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(
                _env_file=None,
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
                _env_file=None,
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key-0123456789",
                CORS_ORIGINS=["https://example.com"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=True,
            )

    def test_production_rejects_wildcard_cors(self) -> None:
        with pytest.raises(ValidationError, match="CORS_ORIGINS"):
            Settings(
                _env_file=None,
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key-0123456789",
                CORS_ORIGINS=["*"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=False,
            )

    def test_production_requires_smtp_host(self) -> None:
        with pytest.raises(ValidationError, match="SMTP_HOST"):
            Settings(
                _env_file=None,
                ENV="production",
                DEBUG=False,
                SECRET_KEY="super-secret-production-key-0123456789",
                CORS_ORIGINS=["https://example.com"],
                ROBOKASSA_MERCHANT_LOGIN="shop",
                ROBOKASSA_PASSWORD1="pass1",
                ROBOKASSA_PASSWORD2="pass2",
                ROBOKASSA_IS_TEST=False,
            )

    def test_production_allows_full_smtp_config(self) -> None:
        settings = Settings(
            _env_file=None,
            ENV="production",
            DEBUG=False,
            SECRET_KEY="super-secret-production-key-0123456789",
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

    def test_production_rejects_short_secret(self) -> None:
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(
                _env_file=None,
                ENV="production",
                DEBUG=False,
                SECRET_KEY="short-key",
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

    def test_non_local_env_enforces_secret_strength(self) -> None:
        # Fail-closed: an ENV that is neither "local" nor "production" (e.g. a
        # mislabeled or staging deploy) must still reject the default signing key,
        # so the app cannot boot with a forgeable token secret.
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(_env_file=None, ENV="staging", SECRET_KEY="change-me")

    def test_local_allows_defaults(self) -> None:
        settings = Settings(
            _env_file=None,
            ENV="local",
            SECRET_KEY="change-me",
        )
        assert settings.is_local is True
        assert settings.SECRET_KEY == "change-me"


_VALID_PRODUCTION = {
    "_env_file": None,
    "ENV": "production",
    "DEBUG": False,
    "SECRET_KEY": "super-secret-production-key-0123456789",
    "CORS_ORIGINS": ["https://example.com"],
    "ROBOKASSA_MERCHANT_LOGIN": "shop",
    "ROBOKASSA_PASSWORD1": "pass1",
    "ROBOKASSA_PASSWORD2": "pass2",
    "ROBOKASSA_IS_TEST": False,
    "SMTP_HOST": "smtp.mail.selcloud.ru",
    "SMTP_USERNAME": "user",
    "SMTP_PASSWORD": "secret",
    "SMTP_FROM_EMAIL": "noreply@otherside-inc.ru",
}


class TestAuthSettingsValidation:
    def test_defaults_meet_the_production_password_hash_baseline(self) -> None:
        settings = Settings(**_VALID_PRODUCTION)
        assert settings.PASSWORD_HASH_MEMORY_COST_KIB >= 19456
        assert settings.PASSWORD_HASH_TIME_COST >= 2

    @pytest.mark.parametrize(
        "override",
        [{"PASSWORD_HASH_TIME_COST": 1}, {"PASSWORD_HASH_MEMORY_COST_KIB": 1024}],
    )
    def test_production_rejects_weak_password_hashing(self, override: dict[str, int]) -> None:
        with pytest.raises(ValidationError, match="PASSWORD_HASH"):
            Settings(**{**_VALID_PRODUCTION, **override})

    def test_local_allows_cheap_password_hashing(self) -> None:
        settings = Settings(_env_file=None, ENV="local", PASSWORD_HASH_TIME_COST=1)
        assert settings.PASSWORD_HASH_TIME_COST == 1

    def test_refresh_token_lifetime_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="REFRESH_TOKEN_EXPIRE_DAYS"):
            Settings(_env_file=None, ENV="local", REFRESH_TOKEN_EXPIRE_DAYS=0)

    def test_hash_concurrency_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="PASSWORD_HASH_MAX_CONCURRENCY"):
            Settings(_env_file=None, ENV="local", PASSWORD_HASH_MAX_CONCURRENCY=0)
