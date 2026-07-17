"""Daily billing lifecycle: trials, renewals, grace, reminder emails."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.enterprise import OrganizationSubscription, SubscriptionPlan
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.services import billing_emails
from app.services import enterprise as ent
from app.services import paystack as paystack_service

logger = logging.getLogger(__name__)


async def _org_admin_email(db: AsyncSession, organization_id: UUID) -> str | None:
    row = await db.execute(
        select(User.email)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .join(Role, Role.id == OrganizationMembership.role_id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == "active",
            Role.slug == "org_admin",
        )
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _mark_email(sub: OrganizationSubscription, key: str) -> bool:
    """Return True if this email key was not yet sent (and mark it)."""
    meta = dict(sub.metadata_ or {})
    sent = dict(meta.get("billing_emails_sent") or {})
    if sent.get(key):
        return False
    sent[key] = utcnow().isoformat()
    meta["billing_emails_sent"] = sent
    sub.metadata_ = meta
    return True


async def run_billing_lifecycle(db: AsyncSession) -> dict[str, Any]:
    await ent.ensure_plans(db)
    now = utcnow()
    stats = {
        "trials_expired": 0,
        "renewals_ok": 0,
        "renewals_failed": 0,
        "grace_advanced": 0,
        "emails": 0,
        "synced": 0,
    }
    subs = list((await db.scalars(select(OrganizationSubscription))).all())
    for sub in subs:
        await ent.sync_subscription_status(db, sub)
        stats["synced"] += 1
        plan = await db.get(SubscriptionPlan, sub.plan_id)
        org = await db.get(Organization, sub.organization_id)
        admin_email = await _org_admin_email(db, sub.organization_id)
        org_name = org.name if org else "Your organization"

        # Trial ending reminders
        if sub.status == "trialing" and sub.trial_ends_at and admin_email:
            days_left = (sub.trial_ends_at.date() - now.date()).days
            if days_left in (7, 3, 1):
                key = f"trial_ending_{days_left}"
                if await _mark_email(sub, key):
                    await billing_emails.trial_ending(
                        admin_email, org_name=org_name, days_left=days_left
                    )
                    stats["emails"] += 1

        if sub.status == "expired":
            stats["trials_expired"] += 1

        # Renewal reminders (3 days before)
        if (
            sub.status == "active"
            and sub.current_period_end
            and admin_email
            and plan
            and plan.code not in {"free", "government"}
        ):
            days_to_renew = (sub.current_period_end.date() - now.date()).days
            if days_to_renew == 3:
                key = "renewal_reminder_3"
                if await _mark_email(sub, key):
                    await billing_emails.renewal_reminder(
                        admin_email,
                        plan_name=plan.name,
                        renew_at=sub.current_period_end.date().isoformat(),
                    )
                    stats["emails"] += 1

        # Auto-renew via Paystack authorization
        if (
            sub.status == "active"
            and sub.provider == "paystack"
            and sub.current_period_end
            and sub.current_period_end <= now + timedelta(hours=12)
            and not sub.cancel_at_period_end
            and plan
            and Decimal(str(plan.price_monthly or 0)) > 0
        ):
            try:
                sub.status = "renewing"
                await db.flush()
                await paystack_service.renew_with_authorization(db, sub=sub, plan=plan)
                stats["renewals_ok"] += 1
                if admin_email:
                    await billing_emails.payment_successful(
                        admin_email,
                        plan_name=plan.name,
                        amount=f"{plan.currency} {plan.price_monthly if sub.billing_period == 'monthly' else plan.price_annual}",
                        reference="renewal",
                    )
                    stats["emails"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("billing.renew_failed org=%s err=%s", sub.organization_id, exc)
                sub.status = "past_due"
                sub.grace_ends_at = now + timedelta(days=7)
                await db.flush()
                stats["renewals_failed"] += 1
                if admin_email and await _mark_email(sub, "payment_failed"):
                    await billing_emails.payment_failed(admin_email, org_name=org_name)
                    stats["emails"] += 1

        if sub.status in {"grace", "past_due"}:
            stats["grace_advanced"] += 1

    await db.flush()
    return stats


async def run_billing_lifecycle_tick() -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        try:
            result = await run_billing_lifecycle(db)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise
