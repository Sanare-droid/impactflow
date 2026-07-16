"""Cross-tenant isolation and RBAC smoke tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_cross_org_program_denied(
    client: AsyncClient, org_a: dict, org_b: dict
):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/programs",
        headers=headers_a,
        json={"name": "Alpha Only Program", "status": "active"},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    denied = await client.get(f"/api/v1/programs/{program_id}", headers=headers_b)
    assert denied.status_code in (403, 404), denied.text

    # Org B listing must not include org A's program
    listed = await client.get("/api/v1/programs", headers=headers_b)
    assert listed.status_code == 200
    assert all(p["id"] != program_id for p in listed.json()["items"])


@pytest.mark.asyncio
async def test_wrong_org_header_denied(client: AsyncClient, org_a: dict, org_b: dict):
    """JWT for org A with X-Organization-Id of org B must not grant access."""
    headers = auth_headers(org_a["access_token"], org_b["organization_id"])
    response = await client.get("/api/v1/programs", headers=headers)
    assert response.status_code in (401, 403), response.text


@pytest.mark.asyncio
async def test_permissions_endpoint(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/me/permissions", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "programs:manage" in body["permissions"] or "organizations:manage" in body[
        "permissions"
    ]
