"""Robokassa payment gateway client."""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal
from urllib.parse import urlencode

from domain.exceptions import PaymentVerificationError


class RobokassaClient:
    """Build payment URLs and verify Robokassa Result URL callbacks."""

    def __init__(
        self,
        merchant_login: str,
        password1: str,
        password2: str,
        *,
        is_test: bool = True,
        payment_base_url: str = "https://auth.robokassa.ru/Merchant/Index.aspx",
    ) -> None:
        self._merchant_login = merchant_login
        self._password1 = password1
        self._password2 = password2
        self._is_test = is_test
        self._payment_base_url = payment_base_url

    def build_payment_url(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        description: str,
    ) -> str:
        """Return redirect URL for the Robokassa payment page."""
        out_sum = self.format_amount(amount)
        signature = self._md5(f"{self._merchant_login}:{out_sum}:{invoice_id}:{self._password1}")
        params = {
            "MerchantLogin": self._merchant_login,
            "OutSum": out_sum,
            "InvId": invoice_id,
            "Description": description,
            "SignatureValue": signature,
            "IsTest": "1" if self._is_test else "0",
        }
        return f"{self._payment_base_url}?{urlencode(params)}"

    def verify_result_signature(
        self,
        *,
        out_sum: str,
        invoice_id: str,
        signature_value: str,
        extra_params: dict[str, str] | None = None,
    ) -> None:
        """Verify Result URL signature (Password #2)."""
        expected = self._build_result_signature(
            out_sum=out_sum,
            invoice_id=invoice_id,
            extra_params=extra_params,
        )
        if not hmac.compare_digest(expected.lower(), signature_value.lower()):
            raise PaymentVerificationError("Invalid Robokassa signature")

    def format_result_response(self, invoice_id: str) -> str:
        """Robokassa expects OK{InvId} on successful webhook processing."""
        return f"OK{invoice_id}"

    def _build_result_signature(
        self,
        *,
        out_sum: str,
        invoice_id: str,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        parts = [out_sum, invoice_id]
        if extra_params:
            for key in sorted(extra_params):
                parts.append(f"{key}={extra_params[key]}")
        parts.append(self._password2)
        return self._md5(":".join(parts))

    @staticmethod
    def format_amount(amount: Decimal) -> str:
        normalized = amount.quantize(Decimal("0.01"))
        return format(normalized, "f")

    @staticmethod
    def amounts_equal(stored: Decimal, received: str) -> bool:
        """Compare callback OutSum with stored amount, tolerating format differences."""
        try:
            return Decimal(received).quantize(Decimal("0.01")) == stored.quantize(Decimal("0.01"))
        except Exception:
            return False

    @staticmethod
    def _md5(value: str) -> str:
        return hashlib.md5(value.encode("utf-8")).hexdigest()
