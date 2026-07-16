"""
Create or update the platform superadmin account.

Usage:
  python -m app.scripts.seed_superadmin

Env (required):
  SUPERADMIN_EMAIL=admin@yourdomain.com
  SUPERADMIN_PASSWORD=YourStrongPass123!

Optional:
  SUPERADMIN_FIRST_NAME=Platform
  SUPERADMIN_LAST_NAME=Admin
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def ensure_superadmin(
    *,
    email: str,
    password: str,
    first_name: str = "Platform",
    last_name: str = "Admin",
) -> User:
    email_norm = email.lower().strip()
    password = password.strip()
    min_len = max(8, int(settings.password_min_length or 8))
    if len(password) < min_len:
        raise ValueError(
            f"SUPERADMIN_PASSWORD must be at least {min_len} characters"
        )

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email_norm))
        if user:
            user.hashed_password = hash_password(password)
            user.is_superuser = True
            user.is_platform_admin = True
            user.is_active = True
            user.email_verified = True
            user.must_change_password = False
            user.password_changed_at = utcnow()
            user.first_name = first_name
            user.last_name = last_name
            await db.commit()
            await db.refresh(user)
            print(f"Updated superadmin: {user.email}")
            return user

        user = User(
            email=email_norm,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_superuser=True,
            is_platform_admin=True,
            is_active=True,
            email_verified=True,
            must_change_password=False,
            password_changed_at=utcnow(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created superadmin: {user.email}")
        return user


async def run() -> None:
    email = os.getenv("SUPERADMIN_EMAIL", "").strip()
    password = os.getenv("SUPERADMIN_PASSWORD", "").strip()
    if not email or not password:
        print(
            "Set SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD before running.",
            file=sys.stderr,
        )
        sys.exit(1)
    await ensure_superadmin(
        email=email,
        password=password,
        first_name=os.getenv("SUPERADMIN_FIRST_NAME", "Platform"),
        last_name=os.getenv("SUPERADMIN_LAST_NAME", "Admin"),
    )


if __name__ == "__main__":
    asyncio.run(run())
