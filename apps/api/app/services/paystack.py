"""Paystack payment adapter for SaaS subscription upgrades."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.db.base import utcnow
from app.models.enterprise import OrganizationSubscription, SubscriptionPlan
from app.models.organization import Organization
from app.models.user import User
from app.services import enterprise as ent
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.paystack_secret_key.strip()}",
        "Content-Type": "application/json",
    }


def amount_to_subunit(price: Decimal | float | int) -> int:
    """Convert plan price (USD catalog) to Paystack subunit (kobo/cents)."""
    usd = Decimal(str(price or 0))
    currency = (settings.paystack_currency or "NGN").upper()
    if currency == "USD":
        local = usd
    else:
        rate = Decimal(str(settings.paystack_usd_to_local or 1600))
        local = usd * rate
    # Paystack amounts are in the smallest currency unit
    return max(0, int((local * 100).quantize(Decimal("1"))))


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    secret = (settings.paystack_secret_key or "").encode("utf-8")
    if not secret or not signature:
        return False
    digest = hmac.new(secret, body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


async def initialize_checkout(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor: User,
    plan_code: str,
    billing_period: str = "monthly",
    callback_url: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    """
    Start a Paystack checkout for a paid plan, or apply free/zero plans immediately.
    When Paystack is not configured, falls back to internal plan change.
    """
    await ent.ensure_plans(db)
    plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if not plan or plan.status != "active":
        raise NotFoundError("Plan not found")

    period = "annual" if billing_period == "annual" else "monthly"
    price = plan.price_annual if period == "annual" else plan.price_monthly
    is_free = Decimal(str(price or 0)) <= 0 or plan.code == "free"

    if is_free or not settings.paystack_enabled:
        sub = await ent.change_subscription(
            db,
            organization_id=organization_id,
            actor_id=actor.id,
            actor_email=actor.email,
            plan_code=plan.code,
            billing_period=period,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if is_free:
            sub.provider = "internal"
        await db.flush()
        return {
            "mode": "activated",
            "provider": sub.provider,
            "subscription": ent.subscription_payload(sub, plan),
            "authorization_url": None,
            "reference": None,
            "public_key": None,
        }

    org = await db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")

    amount = amount_to_subunit(price)
    if amount < 100:
        raise AppError("Plan amount too small for Paystack checkout", status_code=400)

    reference = f"if_{organization_id.hex[:12]}_{secrets.token_hex(8)}"
    frontend = (settings.frontend_url or "").rstrip("/")
    cb = (callback_url or f"{frontend}/app/billing?paystack=1").strip()

    payload = {
        "email": actor.email,
        "amount": amount,
        "currency": (settings.paystack_currency or "NGN").upper(),
        "reference": reference,
        "callback_url": cb,
        "metadata": {
            "organization_id": str(organization_id),
            "plan_code": plan.code,
            "billing_period": period,
            "actor_id": str(actor.id),
            "custom_fields": [
                {"display_name": "Organization", "variable_name": "organization", "value": org.name},
                {"display_name": "Plan", "variable_name": "plan", "value": plan.name},
            ],
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            headers=_headers(),
            json=payload,
        )
    data = response.json() if response.content else {}
    if response.status_code >= 400 or not data.get("status"):
        message = data.get("message") or response.text[:200]
        logger.warning("paystack.initialize_failed status=%s msg=%s", response.status_code, message)
        raise AppError(f"Paystack initialize failed: {message}", status_code=502)

    result = data.get("data") or {}
    sub = await ent.get_or_create_subscription(db, organization_id, plan_code="free")
    meta = dict(sub.metadata_ or {})
    meta["paystack_pending"] = {
        "reference": reference,
        "plan_code": plan.code,
        "billing_period": period,
        "amount": amount,
        "currency": payload["currency"],
        "created_at": utcnow().isoformat(),
    }
    sub.metadata_ = meta
    sub.provider = "paystack"
    await db.flush()

    await write_audit_log(
        db,
        action="billing.paystack_initialize",
        resource_type="organization_subscription",
        resource_id=sub.id,
        organization_id=organization_id,
        actor_id=actor.id,
        actor_email=actor.email,
        description=f"Started Paystack checkout for {plan.code}",
        changes={"reference": reference, "plan": plan.code, "period": period},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        "mode": "checkout",
        "provider": "paystack",
        "authorization_url": result.get("authorization_url"),
        "access_code": result.get("access_code"),
        "reference": reference,
        "public_key": settings.paystack_public_key or None,
        "amount": amount,
        "currency": payload["currency"],
        "plan": {"code": plan.code, "name": plan.name},
        "subscription": ent.subscription_payload(sub, await db.get(SubscriptionPlan, sub.plan_id)),
    }


async def verify_and_activate(
    db: AsyncSession,
    *,
    reference: str,
    actor_id: Optional[UUID] = None,
    actor_email: Optional[str] = None,
) -> dict[str, Any]:
    if not settings.paystack_enabled:
        raise AppError("Paystack is not configured", status_code=400)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=_headers(),
        )
    data = response.json() if response.content else {}
    if response.status_code >= 400 or not data.get("status"):
        message = data.get("message") or "Verification failed"
        raise AppError(f"Paystack verify failed: {message}", status_code=502)

    tx = data.get("data") or {}
    if (tx.get("status") or "").lower() != "success":
        raise AppError(f"Payment not successful ({tx.get('status')})", status_code=400)

    meta = tx.get("metadata") or {}
    org_id_raw = meta.get("organization_id")
    plan_code = meta.get("plan_code")
    period = meta.get("billing_period") or "monthly"
    if not org_id_raw or not plan_code:
        raise AppError("Payment metadata missing organization/plan", status_code=400)

    org_id = UUID(str(org_id_raw))
    sub = await ent.change_subscription(
        db,
        organization_id=org_id,
        actor_id=actor_id,
        actor_email=actor_email or "paystack@system",
        plan_code=str(plan_code),
        billing_period=str(period),
    )
    sub.provider = "paystack"
    sub.provider_customer_id = str(tx.get("customer", {}).get("customer_code") or "") or sub.provider_customer_id
    sub.provider_subscription_id = str(tx.get("id") or reference)
    pending = dict(sub.metadata_ or {})
    pending.pop("paystack_pending", None)
    pending["paystack_last"] = {
        "reference": reference,
        "paid_at": tx.get("paid_at"),
        "amount": tx.get("amount"),
        "currency": tx.get("currency"),
        "channel": tx.get("channel"),
    }
    sub.metadata_ = pending
    await db.flush()

    plan = await db.get(SubscriptionPlan, sub.plan_id)
    return {
        "mode": "activated",
        "provider": "paystack",
        "reference": reference,
        "subscription": ent.subscription_payload(sub, plan),
    }


async def handle_webhook_event(db: AsyncSession, event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event") or ""
    data = event.get("data") or {}
    if event_type == "charge.success":
        reference = data.get("reference")
        if not reference:
            return {"handled": False, "reason": "no_reference"}
        result = await verify_and_activate(db, reference=str(reference))
        return {"handled": True, "event": event_type, **result}
    return {"handled": False, "event": event_type}
