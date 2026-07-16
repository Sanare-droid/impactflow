"""Tests for Epic 7 Enterprise SaaS — billing, flags, domains, onboarding, backups."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_billing_plans_and_subscription(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    plans = await client.get("/api/v1/billing/plans", headers=headers)
    assert plans.status_code == 200, plans.text
    codes = {p["code"] for p in plans.json()["items"]}
    assert "free" in codes
    assert "enterprise" in codes
    assert "government" in codes

    sub = await client.get("/api/v1/billing/subscription", headers=headers)
    assert sub.status_code == 200, sub.text
    assert sub.json()["provider"] == "internal"
    assert sub.json()["plan"]["code"] in codes

    changed = await client.post(
        "/api/v1/billing/subscription/change",
        headers=headers,
        json={"plan_code": "professional", "billing_period": "annual", "coupon_code": "SAVE10"},
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert body["plan"]["code"] == "professional"
    assert body["billing_period"] == "annual"
    assert body["discount_percent"] == 10


@pytest.mark.asyncio
async def test_feature_flags_resolve(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    await client.post(
        "/api/v1/billing/subscription/change",
        headers=headers,
        json={"plan_code": "enterprise"},
    )
    features = await client.get("/api/v1/features", headers=headers)
    assert features.status_code == 200, features.text
    flags = features.json()["features"]
    assert flags.get("ai") is True
    assert flags.get("white_label") is True


@pytest.mark.asyncio
async def test_domains_verify_and_public_host(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/domains",
        headers=headers,
        json={"hostname": "portal.example-ngo.org", "is_primary": True},
    )
    assert created.status_code == 201, created.text
    domain_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert created.json()["verification_token"]

    verified = await client.post(f"/api/v1/domains/{domain_id}/verify", headers=headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "active"
    assert verified.json()["ssl_status"] == "active"

    # Enable branding so public host resolves with org identity
    await client.patch(
        "/api/v1/branding",
        headers=headers,
        json={
            "is_enabled": True,
            "product_name": "Example NGO Portal",
            "primary_color": "#0369A1",
            "metadata": {"footer": "© Example NGO", "terms_url": "https://example-ngo.org/terms"},
        },
    )

    public = await client.get(
        "/api/v1/public/branding-by-host",
        params={"host": "portal.example-ngo.org"},
    )
    assert public.status_code == 200, public.text
    assert public.json()["is_enabled"] is True
    assert public.json()["product_name"] == "Example NGO Portal"


@pytest.mark.asyncio
async def test_onboarding_theme_and_complete(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    state = await client.get("/api/v1/onboarding", headers=headers)
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "in_progress"

    presets = await client.get("/api/v1/onboarding/theme-presets", headers=headers)
    assert presets.status_code == 200
    assert len(presets.json()["items"]) >= 3

    updated = await client.patch(
        "/api/v1/onboarding",
        headers=headers,
        json={
            "complete_step": "theme",
            "theme_preset": "ocean",
            "sector": "health",
            "country_code": "KE",
            "step": "project",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["theme_preset"] == "ocean"
    assert updated.json()["checklist"]["theme"] is True

    branding = await client.get("/api/v1/branding", headers=headers)
    assert branding.json()["primary_color"] == "#0369A1"


@pytest.mark.asyncio
async def test_backup_export_and_sso(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    backup = await client.post(
        "/api/v1/backups",
        headers=headers,
        json={"label": "Nightly"},
    )
    assert backup.status_code == 201, backup.text
    assert backup.json()["status"] == "completed"
    assert backup.json()["checksum"]

    exported = await client.get("/api/v1/backups/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.json()["organization"]["id"] == org_a["organization_id"]

    sso = await client.put(
        "/api/v1/sso",
        headers=headers,
        json={
            "provider": "oidc",
            "config": {"issuer": "https://login.example.com", "client_id": "impactflow"},
            "client_secret": "super-secret-sso",
            "allowed_domains": ["example.com"],
        },
    )
    assert sso.status_code == 200, sso.text
    assert sso.json()["provider"] == "oidc"
    assert "client_secret" not in sso.json().get("config", {})


@pytest.mark.asyncio
async def test_locales_customer_success_plugin_sdk(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    locales = await client.get("/api/v1/locales", headers=headers)
    assert locales.status_code == 200, locales.text
    codes = {x["locale"] for x in locales.json()["items"]}
    assert {"en", "fr", "es", "ar", "pt", "sw"}.issubset(codes)

    cs = await client.get("/api/v1/customer-success", headers=headers)
    assert cs.status_code == 200, cs.text
    assert "health_score" in cs.json()

    ops = await client.get("/api/v1/ops/observability", headers=headers)
    assert ops.status_code == 200, ops.text
    assert ops.json()["api_health"] == "ok"

    sdk = await client.get("/api/v1/plugin-sdk/manifest", headers=headers)
    assert sdk.status_code == 200, sdk.text
    assert "registration_points" in sdk.json()


@pytest.mark.asyncio
async def test_domain_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])

    created = await client.post(
        "/api/v1/domains",
        headers=headers_a,
        json={"hostname": "private.tenant-a.test"},
    )
    assert created.status_code == 201, created.text
    domain_id = created.json()["id"]

    # Org B cannot verify Org A's domain
    blocked = await client.post(f"/api/v1/domains/{domain_id}/verify", headers=headers_b)
    assert blocked.status_code == 404

    list_b = await client.get("/api/v1/domains", headers=headers_b)
    assert list_b.status_code == 200
    assert all(d["hostname"] != "private.tenant-a.test" for d in list_b.json()["items"])
