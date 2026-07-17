"""Outbound email — Resend API, then SMTP, otherwise log stub.

Designed for concurrent invites: shared HTTP client, bounded concurrency,
and fire-and-forget helpers so request handlers never block on delivery.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cap parallel outbound sends so a burst of invites cannot exhaust connections.
_EMAIL_SEMAPHORE = asyncio.Semaphore(8)
_resend_client: Optional[httpx.AsyncClient] = None
_resend_client_lock = asyncio.Lock()


def is_mailer_configured() -> bool:
    return _resend_configured() or _smtp_configured()


def _resend_configured() -> bool:
    return bool((settings.resend_api_key or "").strip())


def _smtp_configured() -> bool:
    return bool((settings.smtp_host or "").strip())


def _using_resend_dev_from() -> bool:
    return "onboarding@resend.dev" in (settings.email_from or "").lower()


async def _get_resend_client() -> httpx.AsyncClient:
    global _resend_client
    async with _resend_client_lock:
        if _resend_client is None or _resend_client.is_closed:
            _resend_client = httpx.AsyncClient(
                timeout=httpx.Timeout(8.0, connect=4.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return _resend_client


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
    async with _EMAIL_SEMAPHORE:
        if _resend_configured():
            try:
                if _using_resend_dev_from():
                    logger.warning(
                        "email.resend_dev_from to=%s — onboarding@resend.dev only "
                        "delivers to the Resend account owner. Set SMTP_FROM to a "
                        "verified domain for real invites.",
                        to,
                    )
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
                return {
                    "status": "sent",
                    "provider": "smtp",
                    "to": to,
                    "subject": subject,
                }
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


def enqueue_email(
    *,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> dict:
    """
    Schedule email delivery without blocking the caller.
    Returns immediately with status=queued (or not_configured).
    """
    if not is_mailer_configured():
        logger.info("email.enqueue_skipped to=%s reason=not_configured", to)
        return {
            "status": "not_configured",
            "provider": "none",
            "to": to,
            "subject": subject,
        }

    async def _run() -> None:
        try:
            result = await send_email(to=to, subject=subject, body=body, html=html)
            if result.get("status") != "sent":
                logger.warning(
                    "email.background_not_sent to=%s status=%s error=%s",
                    to,
                    result.get("status"),
                    result.get("error"),
                )
        except Exception:  # noqa: BLE001
            logger.exception("email.background_failed to=%s", to)

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        # No running loop (sync context) — best-effort skip
        logger.warning("email.enqueue_no_loop to=%s", to)
        return {
            "status": "failed",
            "provider": "none",
            "to": to,
            "subject": subject,
            "error": "no_event_loop",
        }

    provider = "resend" if _resend_configured() else "smtp"
    return {
        "status": "queued",
        "provider": provider,
        "to": to,
        "subject": subject,
        "resend_dev_from": _using_resend_dev_from(),
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

    client = await _get_resend_client()
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
            with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        elif settings.smtp_use_tls:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)

    await asyncio.to_thread(_send)
