"""Object storage for media uploads (S3/MinIO with local filesystem fallback)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_LOCAL_ROOT = Path(__file__).resolve().parents[2] / "var" / "media"


def _s3_client():
    settings = get_settings()
    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        return None
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def store_bytes(
    *,
    organization_id: UUID,
    file_name: str,
    content: bytes,
    content_type: Optional[str] = None,
) -> str:
    """Persist bytes and return a publicly fetchable URL or app-relative media URL."""
    settings = get_settings()
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file_name) or "file"
    key = f"org/{organization_id}/{uuid.uuid4().hex}_{safe_name}"

    client = _s3_client()
    if client is not None:
        try:
            extra = {"ContentType": content_type} if content_type else {}
            client.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=content,
                **extra,
            )
            endpoint = (settings.s3_endpoint_url or "").rstrip("/")
            if endpoint:
                return f"{endpoint}/{settings.s3_bucket}/{key}"
            return f"s3://{settings.s3_bucket}/{key}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("S3 upload failed, falling back to local storage: %s", exc)

    dest = _LOCAL_ROOT / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return f"/api/v1/media/files/{key}"
