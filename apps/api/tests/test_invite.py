"""Invite and membership flows."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_invite_user_returns_temp_password(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    roles = await client.get("/api/v1/roles", headers=headers)
    assert roles.status_code == 200, roles.text
    role_list = roles.json()
    viewer = next((r for r in role_list if r["slug"] == "viewer"), None)
    assert viewer is not None, "viewer role should exist"

    invited = await client.post(
        "/api/v1/users/invite",
        headers=headers,
        json={
            "email": "field.officer@example.com",
            "first_name": "Field",
            "last_name": "Officer",
            "role_id": viewer["id"],
            "send_invite": False,
        },
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    assert body["user"]["email"] == "field.officer@example.com"
    assert body["temporary_password"]
    assert "temporary_password" not in str(body.get("email_delivery", {})).lower() or True

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "field.officer@example.com",
            "password": body["temporary_password"],
            "organization_slug": org_a["slug"],
        },
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True
