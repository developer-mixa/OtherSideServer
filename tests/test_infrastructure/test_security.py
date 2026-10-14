"""Security utility tests."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pytest

from config.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    get_user_id_from_token,
    hash_refresh_token,
)
from config.settings import settings
from domain.exceptions import AuthenticationError


class TestJWT:
    def test_create_and_decode_token(self) -> None:
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id)})
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)

    def test_get_user_id_from_token(self) -> None:
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id)})
        assert get_user_id_from_token(token) == user_id

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token("invalid.token.here")

    def test_token_missing_sub_raises(self) -> None:
        token = create_access_token({})
        with pytest.raises(AuthenticationError):
            get_user_id_from_token(token)

    def test_non_uuid_sub_raises_auth_error_not_500(self) -> None:
        # A correctly signed token whose `sub` is not a UUID must surface as an
        # authentication failure, never bubble up as an unhandled 500.
        token = create_access_token({"sub": "not-a-uuid"})
        with pytest.raises(AuthenticationError) as exc_info:
            get_user_id_from_token(token)
        assert exc_info.value.code == "token_invalid"

    def test_token_without_exp_is_rejected(self) -> None:
        # Signed with the real key, but never expires: must not be accepted.
        token = jwt.encode({"sub": str(uuid4())}, settings.SECRET_KEY, algorithm=settings.JWT_ALG)
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token)
        assert exc_info.value.code == "token_invalid"

    def test_expired_token_is_rejected(self) -> None:
        token = create_access_token({"sub": str(uuid4())}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(AuthenticationError):
            decode_access_token(token)

    def test_alg_none_token_is_rejected(self) -> None:
        token = jwt.encode(
            {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            key=None,
            algorithm="none",
        )
        with pytest.raises(AuthenticationError):
            decode_access_token(token)

    def test_token_carries_issued_at(self) -> None:
        payload = decode_access_token(create_access_token({"sub": str(uuid4())}))
        assert "iat" in payload


class TestRefreshTokenHelpers:
    def test_tokens_are_unique_and_url_safe(self) -> None:
        tokens = {generate_refresh_token() for _ in range(100)}
        assert len(tokens) == 100
        assert all(len(t) >= 43 and t.replace("-", "").replace("_", "").isalnum() for t in tokens)

    def test_hash_is_deterministic_sha256_hex(self) -> None:
        token = generate_refresh_token()
        assert hash_refresh_token(token) == hash_refresh_token(token)
        assert len(hash_refresh_token(token)) == 64
        assert hash_refresh_token(token) != token


class TestNoDeprecatedSecurityLibraries:
    """python-jose (unmaintained, CVE-2024-33663/33664) and passlib (unmaintained, breaks
    on bcrypt>=4.1) were replaced by PyJWT and pwdlib; keep them from creeping back."""

    def test_source_does_not_import_them(self) -> None:
        src_root = Path(__file__).resolve().parents[2] / "src"
        banned = {"jose", "passlib"}
        offenders = []
        for path in src_root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0] in banned]
        assert offenders == []
