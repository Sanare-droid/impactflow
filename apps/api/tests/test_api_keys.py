"""API key authentication."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_api_key_read_access(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={"name": "Key Readable Program", "status": "active"},
    )
    assert created.status_code == 201, created.text

    key_resp = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "CI Reader", "scopes": ["read"]},
    )
    assert key_resp.status_code == 201, key_resp.text
    secret = key_resp.json()["secret"]
    assert secret.startswith("if_")

    # X-Api-Key header
    listed = await client.get(
        "/api/v1/programs",
        headers={
            "X-Api-Key": secret,
            "X-Organization-Id": org_a["organization_id"],
        },
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["meta"]["total"] >= 1

    # Bearer if_… form
    listed_bearer = await client.get(
        "/api/v1/programs",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert listed_bearer.status_code == 200, listed_bearer.text


@pytest.mark.asyncio
async def test_api_key_write_denied_with_read_scope(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    key_resp = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "Read Only", "scopes": ["read"]},
    )
    assert key_resp.status_code == 201, key_resp.text
    secret = key_resp.json()["secret"]

    denied = await client.post(
        "/api/v1/programs",
        headers={"X-Api-Key": secret},
        json={"name": "Should Fail", "status": "active"},
    )
    assert denied.status_code == 403, denied.text


@pytest.mark.asyncio
async def test_api_key_org_mismatch(client: AsyncClient, org_a: dict, org_b: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    key_resp = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "Org Bound", "scopes": ["read"]},
    )
    secret = key_resp.json()["secret"]

    mismatch = await client.get(
        "/api/v1/programs",
        headers={
            "X-Api-Key": secret,
            "X-Organization-Id": org_b["organization_id"],
        },
    )
    assert mismatch.status_code == 403, mismatch.text
