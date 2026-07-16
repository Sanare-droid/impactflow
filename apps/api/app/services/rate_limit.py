"""Redis-backed rate limiting with safe fallback when Redis is unavailable."""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    global _client
    if _client is not None:
        return _client
    try:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
        await _client.ping()
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable for rate limiting: %s", exc)
        _client = None
        return None


async def enforce_rate_limit(
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise AppError(429) when the key exceeds limit within the window."""
    client = await get_redis()
    if client is None:
        # Fail open so local/dev without Redis still works
        return
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)
        if count > limit:
            raise AppError(
                "Too many requests. Please try again later.",
                code="rate_limited",
                status_code=429,
                details={"limit": limit, "window_seconds": window_seconds},
            )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate limit check failed: %s", exc)
