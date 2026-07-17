"""Billing V2.1 — trial, KES plans, Paystack, invoices, grace, enforcement."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_email_verify_token
from app.db.base import utcnow
from app.models.enterprise import SubscriptionPlan
from app.services import enterprise as ent
from app.services.paystack import amount_to_subunit, verify_webhook_signature
from tests.conftest import auth_headers, register_org


@pytest.mark.asyncio
async def test_register_provisions_trial(client: AsyncClient):
    org = await register_org(
        client,
        slug=f"trial-{uuid4().hex[:8]}",
        email=f"trial-{uuid4().hex[:8]}@example.com",
        name="Trial NGO",
    )
    headers = auth_headers(org["access_token"], org["organization_id"])
    sub = await client.get("/api/v1/billing/subscription", headers=headers)
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["plan"]["code"] == "free"
    assert body["status"] == "trialing"
    assert body["days_remaining"] is not None
    assert body["days_remaining"] <= 14


@pytest.mark.asyncio
async def test_verify_email_endpoint(client: AsyncClient):
    org = await register_org(
        client,
        slug=f"verify-{uuid4().hex[:8]}",
        email=f"verify-{uuid4().hex[:8]}@example.com",
        name="Verify NGO",
    )
    token = create_email_verify_token(org["user"]["id"])
    res = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_public_plans_kes_catalog(client: AsyncClient):
    public = await client.get("/api/v1/public/billing/plans")
    assert public.status_code == 200
    items = public.json()["items"]
    by_code = {p["code"]: p for p in items}
    assert "free" in by_code
    assert by_code["free"]["currency"] == "KES"
    assert float(by_code["free"]["price_monthly"] or 0) == 0
    assert float(by_code["starter"]["price_monthly"]) == 9900
    assert by_code["professional"]["recommended"] is True
    assert "government" not in by_code


def test_amount_to_subunit_kes_direct():
    assert amount_to_subunit(7500, "KES") == 750_000
    assert amount_to_subunit(Decimal("20000"), "KES") == 2_000_000


def test_paystack_webhook_signature():
    body = b'{"event":"charge.success"}'
    with patch("app.services.paystack.settings") as settings:
        settings.paystack_secret_key = "sk_test_secret"
        import hashlib
        import hmac

        sig = hmac.new(b"sk_test_secret", body, hashlib.sha512).hexdigest()
        assert verify_webhook_signature(body, sig) is True
        assert verify_webhook_signature(body, "bad") is False


@pytest.mark.asyncio
async def test_government_self_checkout_blocked(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/billing/subscription/change",
        headers=headers,
        json={"plan_code": "government"},
    )
    assert res.status_code == 400, res.text
    body = res.json()
    assert body.get("code") == "contact_sales" or (
        isinstance(body.get("detail"), dict) and body["detail"].get("code") == "contact_sales"
    )


@pytest.mark.asyncio
async def test_cancel_subscription(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/billing/subscription/cancel",
        headers=headers,
        json={"at_period_end": True},
    )
    assert res.status_code == 200, res.text
    assert res.json()["cancel_at_period_end"] is True


@pytest.mark.asyncio
async def test_usage_and_invoices_endpoints(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    usage = await client.get("/api/v1/billing/usage", headers=headers)
    assert usage.status_code == 200, usage.text
    assert "users" in usage.json()
    invoices = await client.get("/api/v1/billing/invoices", headers=headers)
    assert invoices.status_code == 200
    assert "items" in invoices.json()


@pytest.mark.asyncio
async def test_grace_blocks_project_create(client: AsyncClient, org_a: dict, db_session):
    org_id = UUID(org_a["organization_id"])
    sub = await ent.get_or_create_subscription(db_session, org_id)
    sub.status = "grace"
    sub.grace_ends_at = utcnow() + timedelta(days=3)
    await db_session.commit()

    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    prog = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={"name": "Grace Program", "code": f"GP-{uuid4().hex[:6]}"},
    )
    if prog.status_code == 201:
        pid = prog.json()["id"]
        project = await client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "program_id": pid,
                "name": "Blocked Project",
                "code": f"BP-{uuid4().hex[:6]}",
            },
        )
        assert project.status_code == 402
        body = project.json()
        assert body.get("code") == "plan_limit" or (
            isinstance(body.get("detail"), dict) and body["detail"].get("code") == "plan_limit"
        )


@pytest.mark.asyncio
async def test_marketplace_feature_enforced(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    apps = await client.get("/api/v1/marketplace/apps", headers=headers)
    assert apps.status_code == 200
    items = apps.json().get("items") or []
    if not items:
        pytest.skip("no marketplace apps seeded")
    install = await client.post(
        "/api/v1/marketplace/installations",
        headers=headers,
        json={"app_id": items[0]["id"]},
    )
    assert install.status_code == 402
    body = install.json()
    assert body.get("code") == "plan_limit" or (
        isinstance(body.get("detail"), dict) and body["detail"].get("code") == "plan_limit"
    )


@pytest.mark.asyncio
async def test_paystack_initialize_fallback_without_keys(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    with patch("app.services.paystack.settings") as settings:
        settings.paystack_enabled = False
        settings.paystack_secret_key = ""
        settings.paystack_public_key = ""
        settings.paystack_currency = "KES"
        settings.frontend_url = "http://localhost:3000"
        res = await client.post(
            "/api/v1/billing/paystack/initialize",
            headers=headers,
            json={"plan_code": "starter", "billing_period": "monthly"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["mode"] == "activated"


@pytest.mark.asyncio
async def test_create_invoice_and_payload(db_session, org_a: dict):
    await ent.ensure_plans(db_session)
    plan = await db_session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "starter")
    )
    assert plan is not None
    org_id = UUID(org_a["organization_id"])
    sub = await ent.get_or_create_subscription(db_session, org_id)
    inv = await ent.create_invoice(
        db_session,
        organization_id=org_id,
        subscription=sub,
        plan=plan,
        amount=Decimal("7500"),
        currency="KES",
        billing_period="monthly",
        paystack_reference=f"ref_{uuid4().hex[:8]}",
    )
    await db_session.commit()
    payload = ent.invoice_payload(inv)
    assert payload["currency"] == "KES"
    assert payload["amount"] == 7500.0


@pytest.mark.asyncio
async def test_sync_trial_expiry(db_session, org_a: dict):
    org_id = UUID(org_a["organization_id"])
    sub = await ent.get_or_create_subscription(db_session, org_id)
    sub.status = "trialing"
    sub.trial_ends_at = utcnow() - timedelta(days=1)
    await db_session.flush()
    await ent.sync_subscription_status(db_session, sub)
    assert sub.status == "expired"
    await db_session.commit()


@pytest.mark.asyncio
async def test_platform_analytics_requires_admin(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.get("/api/v1/platform/billing/analytics", headers=headers)
    assert res.status_code in (401, 403)
