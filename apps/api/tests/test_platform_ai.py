"""Platform + AI smoke tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_marketplace_list(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/marketplace/apps", headers=headers)
    assert response.status_code == 200, response.text
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_branding_get(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/branding", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["organization_id"] == org_a["organization_id"]


@pytest.mark.asyncio
async def test_ai_prediction_generate(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.post(
        "/api/v1/ai/predictions",
        headers=headers,
        json={"prediction_type": "project_risk"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"]
    assert body["organization_id"] == org_a["organization_id"]


@pytest.mark.asyncio
async def test_notifications_inbox(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    # Generate a prediction to seed a notification for the actor
    await client.post(
        "/api/v1/ai/predictions",
        headers=headers,
        json={"prediction_type": "project_risk"},
    )
    inbox = await client.get("/api/v1/notifications", headers=headers)
    assert inbox.status_code == 200, inbox.text
    unread = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.status_code == 200
    assert "unread_count" in unread.json()
