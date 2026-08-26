"""Tests for transactional email rendering."""

from infrastructure.email.templates import plural_minutes, render_verification_email


class TestPluralMinutes:
    def test_singular(self) -> None:
        assert plural_minutes(1) == "минуту"
        assert plural_minutes(21) == "минуту"

    def test_few(self) -> None:
        assert plural_minutes(2) == "минуты"
        assert plural_minutes(34) == "минуты"

    def test_many(self) -> None:
        assert plural_minutes(5) == "минут"
        assert plural_minutes(15) == "минут"

    def test_teens_are_many_despite_last_digit(self) -> None:
        assert plural_minutes(11) == "минут"
        assert plural_minutes(12) == "минут"
        assert plural_minutes(14) == "минут"


class TestRenderVerificationEmail:
    def test_both_parts_carry_the_code(self) -> None:
        text, html = render_verification_email(
            code="123456", ttl_minutes=15, site_url="https://example.com"
        )
        assert "123456" in text
        # The HTML part spaces the digits so clients don't linkify them as a phone number.
        assert "1 2 3 4 5 6" in html

    def test_validity_is_pluralized(self) -> None:
        text, html = render_verification_email(
            code="123456", ttl_minutes=1, site_url="https://example.com"
        )
        assert "1 минуту" in text
        assert "1 минуту" in html

    def test_site_url_appears_in_both_parts(self) -> None:
        text, html = render_verification_email(
            code="123456", ttl_minutes=15, site_url="https://example.com"
        )
        assert "https://example.com" in text
        assert 'href="https://example.com"' in html

    def test_html_is_self_contained(self) -> None:
        _, html = render_verification_email(
            code="123456", ttl_minutes=15, site_url="https://example.com"
        )
        # External resources are blocked or stripped by mail clients.
        assert "<img" not in html
        assert "<link" not in html
        assert "<script" not in html
