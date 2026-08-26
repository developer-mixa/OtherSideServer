"""SMTP email client — works with Selectel Email Service or any SMTP relay."""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from infrastructure.email.templates import VERIFICATION_SUBJECT, render_verification_email


class SmtpEmailSender:
    """Send transactional email over SMTP."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str = "OtherSide",
        use_tls: bool = True,
        code_ttl_minutes: int = 15,
        site_url: str = "https://otherside-inc.ru",
    ) -> None:
        if not host.strip():
            # aiosmtplib fails deep in the TLS handshake with an opaque
            # "You must set server_hostname when using ssl without a host" — refuse early.
            raise ValueError("SMTP host is required to send email")
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name
        self._use_tls = use_tls
        self._code_ttl_minutes = code_ttl_minutes
        self._site_url = site_url

    async def send_verification_code(self, *, to_email: str, code: str) -> None:
        text, html = render_verification_email(
            code=code,
            ttl_minutes=self._code_ttl_minutes,
            site_url=self._site_url,
        )
        message = EmailMessage()
        message["From"] = f"{self._from_name} <{self._from_email}>"
        message["To"] = to_email
        message["Subject"] = VERIFICATION_SUBJECT
        # Plain text first, HTML second: multipart/alternative means the client picks the
        # last part it can render, so text-only clients still get a usable message.
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
        )
