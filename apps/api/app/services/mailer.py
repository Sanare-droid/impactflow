"""Outbound email — SMTP when configured, otherwise log stub."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(getattr(settings, "smtp_host", "") or "")


async def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> dict:
    """
    Deliver email via SMTP when SMTP_HOST is set; otherwise queue to logs.
    Never log message body (may contain reset links / temp passwords).
    """
    if _smtp_configured():
        try:
            await _send_smtp(to=to, subject=subject, body=body, html=html)
            logger.info("email.sent provider=smtp to=%s subject=%s", to, subject)
            return {"status": "sent", "provider": "smtp", "to": to, "subject": subject}
        except Exception as exc:  # noqa: BLE001
            logger.warning("email.smtp_failed to=%s error=%s", to, exc)
            return {
                "status": "failed",
                "provider": "smtp",
                "to": to,
                "subject": subject,
                "error": str(exc)[:200],
            }

    logger.info(
        "email.queued to=%s subject=%s env=%s frontend=%s",
        to,
        subject,
        settings.app_env,
        settings.frontend_url,
    )
    return {
        "status": "queued_stub",
        "provider": "log",
        "to": to,
        "subject": subject,
    }


async def _send_smtp(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str],
) -> None:
    import asyncio

    def _send() -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from or settings.smtp_user or "noreply@impactflow.local"
        msg["To"] = to
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")
        host = settings.smtp_host
        port = settings.smtp_port
        if settings.smtp_use_tls:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

    await asyncio.to_thread(_send)
