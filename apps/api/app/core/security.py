from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | UUID,
    *,
    organization_id: Optional[str | UUID] = None,
    roles: Optional[list[str]] = None,
    permissions: Optional[list[str]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    if organization_id:
        payload["org_id"] = str(organization_id)
    if roles is not None:
        payload["roles"] = roles
    if permissions is not None:
        payload["permissions"] = permissions
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_email_verify_token(user_id: str | UUID, *, hours: int = 48) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "email_verify",
        "iat": now,
        "exp": now + timedelta(hours=hours),
        "jti": secrets.token_urlsafe(12),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_email_verify_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired verification token") from exc
    if payload.get("type") != "email_verify":
        raise ValueError("Invalid verification token type")
    return UUID(str(payload["sub"]))


def create_refresh_token(subject: str | UUID) -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at). Store only the hash."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    raw = secrets.token_urlsafe(48)
    token_hash = hash_token(raw)
    return raw, token_hash, expire


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def _fernet() -> Fernet:
    key = settings.encryption_key.encode("utf-8")
    try:
        return Fernet(key)
    except Exception:
        if settings.is_production:
            raise RuntimeError(
                "ENCRYPTION_KEY must be a valid Fernet key in production"
            ) from None
        # Stable local-dev fallback derived from JWT secret when ENCRYPTION_KEY
        # is not yet a valid Fernet key.
        digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        import base64

        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt secret") from exc


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def verify_mfa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def mfa_provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.mfa_issuer)
