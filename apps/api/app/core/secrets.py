"""Startup secret validation for production safety."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SNIPPETS = (
    "change_me",
    "replace_with",
    "dev_only",
)
_DEFAULT_ENC_SNIPPETS = (
    "generate_a_fernet",
    "replace_with_fernet",
    "change_me",
)


def validate_runtime_secrets() -> None:
    """
    In production: refuse to start with default / invalid secrets.
    In development: warn only.
    """
    problems: list[str] = []

    jwt = settings.jwt_secret_key or ""
    if len(jwt) < 32:
        problems.append("JWT_SECRET_KEY must be at least 32 characters")
    if any(s in jwt.lower() for s in _DEFAULT_JWT_SNIPPETS):
        problems.append("JWT_SECRET_KEY appears to be a placeholder default")

    enc = (settings.encryption_key or "").strip()
    if not enc or any(s in enc.lower() for s in _DEFAULT_ENC_SNIPPETS):
        problems.append("ENCRYPTION_KEY appears to be a placeholder default")
    else:
        try:
            Fernet(enc.encode("utf-8"))
        except Exception:
            problems.append("ENCRYPTION_KEY is not a valid Fernet key")

    host = (settings.database_host or "").lower()
    if settings.is_production and host in {"", "localhost", "127.0.0.1", "::1"}:
        problems.append(
            "DATABASE_URL points at localhost — on Railway, link the Postgres "
            "plugin to this service (Variables → Add reference → Postgres DATABASE_URL). "
            "Use postgresql+asyncpg://… or postgres://… (auto-normalized)."
        )

    if not problems:
        return

    message = "; ".join(problems)
    if settings.is_production:
        raise RuntimeError(f"Refusing to start in production: {message}")
    logger.warning("Secret hygiene warnings (non-production): %s", message)
