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


@pytest.mark.asyncio
async def test_my_organizations_single_org(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/auth/my-organizations", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == org_a["organization_id"]
    assert items[0]["is_primary"] is True


@pytest.mark.asyncio
async def test_my_organizations_multi_org_picker(client: AsyncClient, org_a: dict, org_b: dict):
    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    roles = await client.get("/api/v1/roles", headers=headers_b)
    assert roles.status_code == 200, roles.text
    member_role = next(r for r in roles.json() if r["slug"] in ("member", "org_admin"))

    invited = await client.post(
        "/api/v1/users/invite",
        headers=headers_b,
        json={
            "email": org_a["email"],
            "first_name": "Alpha",
            "last_name": "Admin",
            "role_id": member_role["id"],
            "send_invite": False,
        },
    )
    assert invited.status_code == 201, invited.text

    # Login without specifying an org slug — resolves to the user's primary org (A).
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": org_a["email"], "password": org_a["password"]},
    )
    assert login.status_code == 200, login.text
    access_token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/my-organizations",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 2
    ids = {i["id"] for i in items}
    assert org_a["organization_id"] in ids
    assert org_b["organization_id"] in ids
    primary = next(i for i in items if i["is_primary"])
    assert primary["id"] == org_a["organization_id"]
