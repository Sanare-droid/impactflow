"""Paystack payment adapter for SaaS subscription upgrades (KES catalog)."""

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
from app.services import billing_emails
from app.services import enterprise as ent
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.paystack_secret_key.strip()}",
        "Content-Type": "application/json",
    }


def amount_to_subunit(price: Decimal | float | int, currency: str | None = None) -> int:
    """Convert plan price in catalog currency (KES) to Paystack subunit (cents)."""
    amount = Decimal(str(price or 0))
    # Catalog is stored in KES (or other local currency) — charge directly.
    _ = (currency or settings.paystack_currency or "KES").upper()
    return max(0, int((amount * 100).quantize(Decimal("1"))))


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
    if plan.code == "government":
        raise AppError(
            "Government plans require sales. Contact sales to continue.",
            code="contact_sales",
            status_code=400,
        )

    period = "annual" if billing_period == "annual" else "monthly"
    price = plan.price_annual if period == "annual" else plan.price_monthly
    is_free = Decimal(str(price or 0)) <= 0 or plan.code == "free"
    currency = (plan.currency or settings.paystack_currency or "KES").upper()

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

    amount = amount_to_subunit(price, currency)
    if amount < 100:
        raise AppError("Plan amount too small for Paystack checkout", status_code=400)

    sub = await ent.get_or_create_subscription(db, organization_id, plan_code="free")
    reference = f"if_{organization_id.hex[:12]}_{secrets.token_hex(8)}"
    frontend = (settings.frontend_url or "").rstrip("/")
    cb = (callback_url or f"{frontend}/app/billing?paystack=1").strip()

    payload = {
        "email": actor.email,
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "callback_url": cb,
        "metadata": {
            "organization_id": str(organization_id),
            "tenant_id": str(organization_id),
            "subscription_id": str(sub.id),
            "plan_id": str(plan.id),
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
    meta = dict(sub.metadata_ or {})
    meta["paystack_pending"] = {
        "reference": reference,
        "plan_code": plan.code,
        "billing_period": period,
        "amount": amount,
        "currency": currency,
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
        "currency": currency,
        "plan": {"code": plan.code, "name": plan.name},
        "subscription": ent.subscription_payload(sub, await db.get(SubscriptionPlan, sub.plan_id)),
    }


async def _activate_from_tx(
    db: AsyncSession,
    *,
    tx: dict[str, Any],
    reference: str,
    actor_id: Optional[UUID] = None,
    actor_email: Optional[str] = None,
) -> dict[str, Any]:
    meta = tx.get("metadata") or {}
    org_id_raw = meta.get("organization_id") or meta.get("tenant_id")
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
    customer = tx.get("customer") or {}
    authorization = tx.get("authorization") or {}
    sub.provider_customer_id = str(customer.get("customer_code") or "") or sub.provider_customer_id
    sub.provider_subscription_id = str(tx.get("id") or reference)
    pending = dict(sub.metadata_ or {})
    pending.pop("paystack_pending", None)
    if authorization.get("authorization_code"):
        pending["paystack_authorization"] = {
            "authorization_code": authorization.get("authorization_code"),
            "card_type": authorization.get("card_type"),
            "last4": authorization.get("last4"),
            "exp_month": authorization.get("exp_month"),
            "exp_year": authorization.get("exp_year"),
            "bank": authorization.get("bank"),
            "reusable": authorization.get("reusable"),
        }
    pending["paystack_last"] = {
        "reference": reference,
        "paid_at": tx.get("paid_at"),
        "amount": tx.get("amount"),
        "currency": tx.get("currency"),
        "channel": tx.get("channel"),
    }
    # reset email markers for next cycle
    pending["billing_emails_sent"] = {}
    sub.metadata_ = pending
    await db.flush()

    plan = await db.get(SubscriptionPlan, sub.plan_id)
    amount_major = Decimal(str(tx.get("amount") or 0)) / Decimal("100")
    currency = str(tx.get("currency") or (plan.currency if plan else "KES")).upper()
    inv = await ent.create_invoice(
        db,
        organization_id=org_id,
        subscription=sub,
        plan=plan,
        amount=amount_major,
        currency=currency,
        billing_period=str(period),
        status="paid",
        paystack_reference=reference,
        receipt_url=None,
        metadata={"channel": tx.get("channel"), "gateway_response": tx.get("gateway_response")},
    )

    email = actor_email
    if not email and actor_id:
        user = await db.get(User, actor_id)
        email = user.email if user else None
    if email and plan:
        amount_label = f"{currency} {amount_major:,.2f}"
        await billing_emails.payment_successful(
            email, plan_name=plan.name, amount=amount_label, reference=reference
        )
        await billing_emails.invoice_email(
            email, invoice_number=inv.number, amount=amount_label, plan_name=plan.name
        )
        await billing_emails.upgrade_confirmation(email, plan_name=plan.name)

    await write_audit_log(
        db,
        action="billing.payment_success",
        resource_type="billing_invoice",
        resource_id=inv.id,
        organization_id=org_id,
        actor_id=actor_id,
        actor_email=email or "paystack@system",
        description=f"Paystack payment activated {plan_code}",
        changes={"reference": reference, "invoice": inv.number},
    )

    return {
        "mode": "activated",
        "provider": "paystack",
        "reference": reference,
        "invoice": ent.invoice_payload(inv),
        "subscription": ent.subscription_payload(sub, plan),
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

    # Idempotent: existing paid invoice for this reference
    from app.models.enterprise import BillingInvoice

    existing = await db.scalar(
        select(BillingInvoice).where(BillingInvoice.paystack_reference == reference)
    )
    if existing and existing.status == "paid":
        sub = await db.get(OrganizationSubscription, existing.subscription_id)
        plan = await db.get(SubscriptionPlan, existing.plan_id) if existing.plan_id else None
        return {
            "mode": "activated",
            "provider": "paystack",
            "reference": reference,
            "invoice": ent.invoice_payload(existing),
            "subscription": ent.subscription_payload(sub, plan) if sub else None,
        }

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

    return await _activate_from_tx(
        db, tx=tx, reference=reference, actor_id=actor_id, actor_email=actor_email
    )


async def renew_with_authorization(
    db: AsyncSession,
    *,
    sub: OrganizationSubscription,
    plan: SubscriptionPlan,
) -> dict[str, Any]:
    """Charge saved authorization for renewal."""
    if not settings.paystack_enabled:
        raise AppError("Paystack is not configured", status_code=400)
    meta = dict(sub.metadata_ or {})
    auth = meta.get("paystack_authorization") or {}
    code = auth.get("authorization_code")
    if not code:
        raise AppError("No reusable Paystack authorization on file", status_code=400)

    period = sub.billing_period or "monthly"
    price = plan.price_annual if period == "annual" else plan.price_monthly
    currency = (plan.currency or "KES").upper()
    amount = amount_to_subunit(price, currency)
    reference = f"if_rn_{sub.organization_id.hex[:10]}_{secrets.token_hex(6)}"

    # Prefer customer email from org admin / metadata
    email = (meta.get("billing_email") or "").strip()
    if not email:
        org = await db.get(Organization, sub.organization_id)
        email = (org.email if org else None) or "billing@impactflow.app"

    payload = {
        "authorization_code": code,
        "email": email,
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "metadata": {
            "organization_id": str(sub.organization_id),
            "tenant_id": str(sub.organization_id),
            "subscription_id": str(sub.id),
            "plan_id": str(plan.id),
            "plan_code": plan.code,
            "billing_period": period,
            "renewal": True,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE}/transaction/charge_authorization",
            headers=_headers(),
            json=payload,
        )
    data = response.json() if response.content else {}
    if response.status_code >= 400 or not data.get("status"):
        message = data.get("message") or response.text[:200]
        raise AppError(f"Paystack renewal failed: {message}", status_code=502)

    tx = data.get("data") or {}
    if (tx.get("status") or "").lower() != "success":
        raise AppError(f"Renewal not successful ({tx.get('status')})", status_code=400)

    # Ensure metadata has plan codes for activation path
    tx_meta = dict(tx.get("metadata") or {})
    tx_meta.update(payload["metadata"])
    tx["metadata"] = tx_meta
    return await _activate_from_tx(db, tx=tx, reference=reference)


async def handle_webhook_event(db: AsyncSession, event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event") or ""
    data = event.get("data") or {}
    if event_type == "charge.success":
        reference = data.get("reference")
        if not reference:
            return {"handled": False, "reason": "no_reference"}
        result = await verify_and_activate(db, reference=str(reference))
        return {"handled": True, "event": event_type, **result}
    if event_type in {"charge.failed", "invoice.payment_failed"}:
        meta = data.get("metadata") or {}
        org_id_raw = meta.get("organization_id")
        if org_id_raw:
            org_id = UUID(str(org_id_raw))
            sub = await ent.get_or_create_subscription(db, org_id)
            sub.status = "past_due"
            sub.grace_ends_at = utcnow()
            from datetime import timedelta

            sub.grace_ends_at = utcnow() + timedelta(days=7)
            await db.flush()
            return {"handled": True, "event": event_type, "status": "past_due"}
        return {"handled": False, "reason": "no_org"}
    return {"handled": False, "event": event_type}
