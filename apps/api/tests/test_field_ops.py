"""Tests for Epic 4 field operations — devices, batch sync, delta pull."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_register_device(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/devices/register",
        headers=headers,
        json={
            "device_key": f"test-device-{uuid4().hex[:8]}",
            "name": "Officer Phone",
            "platform": "android",
            "app_version": "1.0.0",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "Officer Phone"
    assert body["status"] == "active"
    assert body["platform"] == "android"


@pytest.mark.asyncio
async def test_batch_push_beneficiary(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    mutation_id = f"mut-{uuid4().hex}"
    res = await client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": mutation_id,
                    "entity_type": "beneficiary",
                    "op": "create",
                    "local_id": f"local-{uuid4().hex[:8]}",
                    "payload": {
                        "first_name": "Offline",
                        "last_name": "Beneficiary",
                        "phone": "+254700000001",
                        "consent_data_use": True,
                    },
                }
            ],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["applied"] == 1
    assert body["failed"] == 0
    assert body["results"][0]["status"] == "applied"
    assert body["results"][0]["server_id"]

    # Idempotent retry
    retry = await client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={"mutations": [{"client_mutation_id": mutation_id, "entity_type": "beneficiary", "op": "create", "local_id": "x", "payload": {}}]},
    )
    assert retry.status_code == 200
    assert retry.json()["results"][0]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_delta_pull(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/sync/pull",
        headers=headers,
        json={"entities": ["beneficiaries", "surveys", "tasks", "notifications"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "server_time" in body
    assert "sync_token" in body
    assert "beneficiaries" in body


@pytest.mark.asyncio
async def test_sync_run_session(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    device = await client.post(
        "/api/v1/devices/register",
        headers=headers,
        json={
            "device_key": f"sync-run-{uuid4().hex[:8]}",
            "name": "Sync Test",
            "platform": "ios",
            "app_version": "1.0.0",
        },
    )
    device_id = device.json()["id"]
    res = await client.post(
        "/api/v1/sync/run",
        headers=headers,
        json={
            "device_id": device_id,
            "client_version": "1.0.0",
            "pull": {"entities": ["beneficiaries"]},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["session_id"]
    assert body["status"] in ("completed", "partial", "failed")

    sessions = await client.get("/api/v1/sync/sessions", headers=headers)
    assert sessions.status_code == 200
    assert sessions.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_device_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/devices/register",
        headers=headers_a,
        json={
            "device_key": f"iso-{uuid4().hex[:8]}",
            "name": "Org A Device",
            "platform": "android",
        },
    )
    device_id = created.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    res = await client.patch(
        f"/api/v1/devices/{device_id}",
        headers=headers_b,
        json={"status": "revoked"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_field_ops_metrics(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.get("/api/v1/field-ops/metrics", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "active_devices" in body
    assert "sync_sessions" in body


@pytest.mark.asyncio
async def test_upload_media_binary_fills_remote_url(client: AsyncClient, org_a: dict):
    """Real multipart upload should persist bytes and return a fetchable remote_url
    (S3/MinIO when configured, local filesystem fallback otherwise) — not a stub."""
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/media/uploads/binary",
        headers=headers,
        data={
            "client_mutation_id": f"media-{uuid4().hex}",
            "entity_type": "survey_response",
        },
        files={"file": ("photo.jpg", b"fake-jpeg-bytes", "image/jpeg")},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "uploaded"
    assert body["remote_url"]
    assert body["file_name"] == "photo.jpg"
    assert body["mime_type"] == "image/jpeg"

    # Listed back under the org's media uploads.
    listed = await client.get("/api/v1/media/uploads", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json()["items"])
