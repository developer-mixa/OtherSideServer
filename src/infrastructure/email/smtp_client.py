"""SMTP email client — works with Selectel Email Service or any SMTP relay."""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib


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

    async def send_verification_code(self, *, to_email: str, code: str) -> None:
        message = EmailMessage()
        message["From"] = f"{self._from_name} <{self._from_email}>"
        message["To"] = to_email
        message["Subject"] = "Код подтверждения почты OtherSide"
        message.set_content(
            f"Ваш код подтверждения: {code}\n\n"
            f"Код действителен {self._code_ttl_minutes} минут. Если вы не регистрировались "
            "на OtherSide, просто проигнорируйте это письмо."
        )
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
        )
