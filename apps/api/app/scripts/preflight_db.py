"""Fail fast before migrations if DATABASE_URL is missing/localhost in production."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from app.core.config import normalize_database_url


def main() -> int:
    app_env = (os.getenv("APP_ENV") or "development").lower()
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        if app_env == "production":
            print(
                "ERROR: DATABASE_URL is not set. On Railway: API service → Variables → "
                "Add reference → Postgres DATABASE_URL (${{Postgres.DATABASE_URL}}).",
                file=sys.stderr,
            )
            return 1
        print("WARNING: DATABASE_URL unset; using app defaults (localhost).", file=sys.stderr)
        return 0

    url = normalize_database_url(raw)
    host = (urlparse(url).hostname or "").lower()
    if app_env == "production" and host in {"", "localhost", "127.0.0.1", "::1"}:
        print(
            f"ERROR: DATABASE_URL host is '{host or '(empty)'}' — migrations cannot "
            "reach Postgres inside the container. Link Railway Postgres to this service "
            "(Variables → Add reference → DATABASE_URL) and redeploy.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
