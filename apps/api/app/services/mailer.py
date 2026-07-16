"""Outbound email — Resend API, then SMTP, otherwise log stub."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _resend_configured() -> bool:
    return bool((settings.resend_api_key or "").strip())


def _smtp_configured() -> bool:
    return bool((settings.smtp_host or "").strip())


async def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> dict:
    """
    Deliver email via Resend (RESEND_API_KEY) or SMTP when configured;
    otherwise queue to logs. Never log message body (may contain reset links).
    """
    if _resend_configured():
        try:
            result = await _send_resend(to=to, subject=subject, body=body, html=html)
            logger.info("email.sent provider=resend to=%s subject=%s", to, subject)
            return {
                "status": "sent",
                "provider": "resend",
                "to": to,
                "subject": subject,
                **result,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("email.resend_failed to=%s error=%s", to, exc)
            return {
                "status": "failed",
                "provider": "resend",
                "to": to,
                "subject": subject,
                "error": str(exc)[:200],
            }

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


async def _send_resend(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str],
) -> dict:
    payload: dict = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"Resend HTTP {response.status_code}: {detail}")
        data = response.json() if response.content else {}
        return {"id": data.get("id")}


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
        msg["From"] = settings.email_from
        msg["To"] = to
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")
        host = settings.smtp_host
        port = int(settings.smtp_port or 587)
        user = (settings.smtp_user or "").strip()
        password = settings.smtp_password or ""
        # 465 / 2465 = implicit SSL; 587 / 2587 = STARTTLS
        use_ssl = port in {465, 2465}
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        elif settings.smtp_use_tls:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)

    await asyncio.to_thread(_send)
