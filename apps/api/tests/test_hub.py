"""Tests for Epic 6 Integrations Hub — connectors, mapping, monitoring, webhooks."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_connectors_catalog(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.get("/api/v1/connectors", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    codes = {c["code"] for c in items}
    assert "kobo" in codes
    assert "slack" in codes
    assert "microsoft-365" in codes
    assert "quickbooks" in codes
    assert "power-bi" in codes


@pytest.mark.asyncio
async def test_enable_connector_and_health(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    enabled = await client.post(
        "/api/v1/connectors/enable",
        headers=headers,
        json={
            "connector_code": "csv-analytics",
            "name": "Analytics CSV",
            "config": {},
        },
    )
    assert enabled.status_code == 201, enabled.text
    integ_id = enabled.json()["id"]

    health = await client.post(f"/api/v1/integrations/{integ_id}/health", headers=headers)
    assert health.status_code == 200, health.text
    assert health.json()["healthy"] is True

    sync = await client.post(
        f"/api/v1/integrations/{integ_id}/sync",
        headers=headers,
        json={"mode": "dry_run", "direction": "push", "dry_run": True},
    )
    assert sync.status_code == 200, sync.text
    assert sync.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_encrypted_secret_on_enable(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    enabled = await client.post(
        "/api/v1/connectors/enable",
        headers=headers,
        json={
            "connector_code": "webhook-producer",
            "name": "Outbound Hook",
            "endpoint_url": "https://example.com/hooks/if",
            "secret": "super-secret-value-1234",
            "config": {"shared_secret": "super-secret-value-1234"},
            "events": ["report.published"],
        },
    )
    assert enabled.status_code == 201, enabled.text
    cfg = enabled.json()["config"]
    assert cfg.get("has_secret") is True
    assert "shared_secret" not in cfg or cfg.get("shared_secret") is None
    assert "_encrypted" not in cfg


@pytest.mark.asyncio
async def test_field_mapping_preview(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/field-mappings",
        headers=headers,
        json={
            "name": "Kobo Beneficiary Map",
            "entity_type": "beneficiary",
            "connector_code": "kobo",
            "mappings": [
                {"source": "first", "target": "first_name"},
                {"source": "last", "target": "last_name"},
            ],
            "defaults": {"consent_data_use": True},
            "validation_rules": [{"field": "first_name", "required": True}],
        },
    )
    assert created.status_code == 201, created.text
    mid = created.json()["id"]

    preview = await client.post(
        f"/api/v1/field-mappings/{mid}/preview",
        headers=headers,
        json={"sample": {"first": "Amina", "last": "Okello"}},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["valid"] is True
    assert body["mapped"]["first_name"] == "Amina"
    assert body["mapped"]["consent_data_use"] is True


@pytest.mark.asyncio
async def test_monitoring_and_developer_portal(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    mon = await client.get("/api/v1/integrations/monitoring", headers=headers)
    assert mon.status_code == 200, mon.text
    assert "connected_systems" in mon.json()
    assert "success_rate" in mon.json()

    portal = await client.get("/api/v1/developer/portal", headers=headers)
    assert portal.status_code == 200, portal.text
    assert portal.json()["openapi_url"] == "/openapi.json"
    assert len(portal.json()["events"]) > 5
    assert len(portal.json()["connectors"]) > 10

    events = await client.get("/api/v1/developer/events", headers=headers)
    assert events.status_code == 200
    assert any(e["code"] == "webhook.received" for e in events.json()["items"])

    plugins = await client.get("/api/v1/plugins", headers=headers)
    assert plugins.status_code == 200
    assert any(p["code"] == "connector-framework" for p in plugins.json()["items"])


@pytest.mark.asyncio
async def test_inbound_webhook_emits_event(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    enabled = await client.post(
        "/api/v1/connectors/enable",
        headers=headers,
        json={
            "connector_code": "webhook-consumer",
            "name": "Inbound",
            "config": {"path_token": "test-token-abc", "shared_secret": "sig-secret"},
        },
    )
    assert enabled.status_code == 201, enabled.text

    inbound = await client.post(
        "/api/v1/webhooks/inbound/test-token-abc",
        headers={"X-Organization-Id": org_a["organization_id"]},
        json={"event": "webhook.received", "title": "External ping", "body": "hello"},
    )
    assert inbound.status_code == 200, inbound.text
    assert inbound.json()["accepted"] is True


@pytest.mark.asyncio
async def test_hub_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    enabled = await client.post(
        "/api/v1/connectors/enable",
        headers=headers_a,
        json={"connector_code": "email", "name": "Mail A", "config": {"from_address": "a@ex.com"}},
    )
    integ_id = enabled.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    res = await client.post(f"/api/v1/integrations/{integ_id}/health", headers=headers_b)
    assert res.status_code == 404
