import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_org


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    org = await register_org(
        client, slug="hope-foundation", email="admin@hope.org"
    )
    assert org["access_token"]
    assert org["user"]["email"] == "admin@hope.org"

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@hope.org",
            "password": "SecurePass123!",
            "organization_slug": "hope-foundation",
        },
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin-alpha@example.com"
