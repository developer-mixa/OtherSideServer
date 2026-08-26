"""Fallback email sender for local development, when no SMTP relay is configured."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Log the verification code instead of sending it.

    Used only when SMTP_HOST is empty, which settings validation forbids in production.
    Without it a developer with no SMTP relay gets a registered account and no way to
    ever learn the code.
    """

    async def send_verification_code(self, *, to_email: str, code: str) -> None:
        logger.warning(
            "SMTP is not configured — verification code for %s is %s (not emailed)",
            to_email,
            code,
        )
