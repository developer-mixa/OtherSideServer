"""Robokassa client tests."""

from decimal import Decimal

import pytest

from domain.exceptions import PaymentVerificationError
from infrastructure.payments.robokassa import RobokassaClient


@pytest.fixture
def robokassa() -> RobokassaClient:
    return RobokassaClient(
        merchant_login="demo",
        password1="pass1",
        password2="pass2",
        is_test=True,
    )


class TestRobokassaClient:
    def test_build_payment_url_contains_signature(self, robokassa: RobokassaClient) -> None:
        url = robokassa.build_payment_url(
            invoice_id="1001",
            amount=Decimal("499.00"),
            description="Remove ads",
        )
        assert "MerchantLogin=demo" in url
        assert "InvId=1001" in url
        assert "OutSum=499.00" in url
        assert "SignatureValue=" in url
        assert "IsTest=1" in url

    def test_verify_result_signature_valid(self, robokassa: RobokassaClient) -> None:
        import hashlib

        out_sum = "499.00"
        invoice_id = "1001"
        signature = hashlib.md5(f"{out_sum}:{invoice_id}:pass2".encode()).hexdigest()
        robokassa.verify_result_signature(
            out_sum=out_sum,
            invoice_id=invoice_id,
            signature_value=signature,
        )

    def test_verify_result_signature_invalid(self, robokassa: RobokassaClient) -> None:
        with pytest.raises(PaymentVerificationError):
            robokassa.verify_result_signature(
                out_sum="499.00",
                invoice_id="1001",
                signature_value="bad-signature",
            )

    def test_format_result_response(self, robokassa: RobokassaClient) -> None:
        assert robokassa.format_result_response("1001") == "OK1001"

    def test_amounts_equal_tolerates_format_differences(self) -> None:
        assert RobokassaClient.amounts_equal(Decimal("499.00"), "499")
        assert RobokassaClient.amounts_equal(Decimal("499"), "499.00")
        assert not RobokassaClient.amounts_equal(Decimal("499.00"), "500")
