"""Shared pytest fixtures for ImpactFlow API tests."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

# Ensure all models are registered on Base.metadata
import app.db  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _disable_rate_limits(monkeypatch):
    """Tests must not hit Redis rate limits shared with the running API container."""

    async def _noop(*, key: str, limit: int, window_seconds: int) -> None:
        return None

    monkeypatch.setattr("app.services.rate_limit.enforce_rate_limit", _noop)
    monkeypatch.setattr("app.api.v1.auth.enforce_rate_limit", _noop)
    monkeypatch.setattr("app.api.v1.ai.enforce_rate_limit", _noop)
    monkeypatch.setattr("app.api.v1.platform.enforce_rate_limit", _noop)


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


async def register_org(
    client: AsyncClient,
    *,
    slug: str,
    email: str,
    password: str = "SecurePass123!",
    name: str | None = None,
) -> dict[str, Any]:
    payload = {
        "organization_name": name or slug.replace("-", " ").title(),
        "organization_slug": slug,
        "organization_type": "ngo",
        "country_code": "KE",
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "Admin",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    return {
        "tokens": data,
        "access_token": data["access_token"],
        "user": data["user"],
        "organization_id": data["user"]["primary_organization_id"],
        "slug": slug,
        "email": email,
        "password": password,
    }


def auth_headers(access_token: str, organization_id: str | UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Organization-Id": str(organization_id),
    }


@pytest.fixture
async def org_a(client: AsyncClient) -> dict[str, Any]:
    return await register_org(
        client, slug="org-alpha", email="admin-alpha@example.com"
    )


@pytest.fixture
async def org_b(client: AsyncClient) -> dict[str, Any]:
    return await register_org(
        client, slug="org-beta", email="admin-beta@example.com"
    )
