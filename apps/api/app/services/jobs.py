"""Background job tick: webhook delivery retries + overdue task scans."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.notification import WebhookDelivery
from app.models.platform import IntegrationConnection
from app.models.task import Task
from app.services import workflows
from app.services.events import EVENT_INTEGRATION_ERROR, EVENT_TASK_OVERDUE, emit_event

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = [60, 300, 900, 3600, 7200]
EVENT_BUDGET_BURN = "budget.burn"
EVENT_GRANT_EXPIRING = "grant.expiring"


def _slack_body(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("title") or payload.get("event") or "ImpactFlow event"
    body = payload.get("body") or ""
    return {
        "text": f"*{text}*\n{body}" if body else text,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{text}*\n{body}" if body else f"*{text}*",
                },
            }
        ],
    }


async def _deliver_one(db: AsyncSession, delivery: WebhookDelivery) -> None:
    integ = await db.get(IntegrationConnection, delivery.integration_id)
    url = delivery.endpoint_url or (integ.endpoint_url if integ else None)
    if not url:
        delivery.status = "dead"
        delivery.last_error = "Missing endpoint URL"
        return

    delivery.status = "processing"
    delivery.attempt_count = (delivery.attempt_count or 0) + 1
    await db.flush()

    provider = integ.provider if integ else "webhook"
    body: Any = delivery.payload
    headers = {"Content-Type": "application/json", "User-Agent": "ImpactFlow-Webhooks/1.0"}
    if provider == "slack":
        body = _slack_body(delivery.payload)

    # HMAC signature when encrypted shared_secret is present
    if integ:
        try:
            from app.services.connectors.runtime import (
                compute_webhook_signature,
                signing_secret_from_config,
            )

            secret = signing_secret_from_config(integ.config or {})
            if secret:
                raw = json.dumps(body, default=str, separators=(",", ":")).encode("utf-8")
                headers["X-ImpactFlow-Signature"] = compute_webhook_signature(secret, raw)
        except Exception:  # noqa: BLE001
            pass

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=body, headers=headers)
        delivery.response_status = resp.status_code
        if 200 <= resp.status_code < 300:
            delivery.status = "delivered"
            delivery.delivered_at = utcnow()
            delivery.last_error = None
            delivery.next_attempt_at = None
            if integ:
                integ.last_sync_at = utcnow()
                integ.last_error = None
                integ.status = "active"
            return

        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    except Exception as exc:  # noqa: BLE001
        err = str(exc)[:1000]
        delivery.last_error = err
        if integ:
            integ.last_error = err
        if delivery.attempt_count >= (delivery.max_attempts or 5):
            delivery.status = "dead"
            delivery.next_attempt_at = None
            if integ:
                integ.status = "error"
            await emit_event(
                db,
                organization_id=delivery.organization_id,
                event_type=EVENT_INTEGRATION_ERROR,
                title=f"Integration delivery failed: {integ.name if integ else 'webhook'}",
                body=err,
                link="/app/integrations",
                severity="warning",
                resource_type="integration_connection",
                resource_id=str(delivery.integration_id),
                role_slugs=["org_admin", "manager"],
                metadata={"delivery_id": str(delivery.id)},
                enqueue_outbound=False,
            )
        else:
            delay = BACKOFF_SECONDS[min(delivery.attempt_count - 1, len(BACKOFF_SECONDS) - 1)]
            delivery.status = "pending"
            delivery.next_attempt_at = utcnow() + timedelta(seconds=delay)


async def process_webhook_queue(db: AsyncSession, *, limit: int = 25) -> int:
    now = utcnow()
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(
            WebhookDelivery.status == "pending",
            (WebhookDelivery.next_attempt_at.is_(None))
            | (WebhookDelivery.next_attempt_at <= now),
        )
        .order_by(WebhookDelivery.created_at.asc())
        .limit(limit)
    )
    processed = 0
    for delivery in rows:
        await _deliver_one(db, delivery)
        processed += 1
    await db.flush()
    return processed


async def scan_overdue_tasks(db: AsyncSession) -> int:
    """Notify assignees/managers about overdue open tasks (once per day via metadata flag)."""
    today = date.today()
    tasks = await db.scalars(
        select(Task).where(
            Task.due_date.is_not(None),
            Task.due_date < today,
            Task.status.in_(["todo", "in_progress", "blocked"]),
        )
    )
    emitted = 0
    for task in tasks:
        meta = dict(task.metadata_ or {})
        flag = meta.get("overdue_notified_on")
        if flag == today.isoformat():
            continue
        await emit_event(
            db,
            organization_id=task.organization_id,
            event_type=EVENT_TASK_OVERDUE,
            title=f"Overdue task: {task.title}",
            body=f"Due {task.due_date}. Status: {task.status}.",
            link="/app/tasks",
            severity="warning",
            resource_type="task",
            resource_id=str(task.id),
            role_slugs=["org_admin", "manager"],
            metadata={"due_date": str(task.due_date)},
        )
        # Also notify assignee directly if set
        if task.assignee_id:
            from app.services.notifications import create_notification

            await create_notification(
                db,
                organization_id=task.organization_id,
                user_id=task.assignee_id,
                event_type=EVENT_TASK_OVERDUE,
                title=f"Your task is overdue: {task.title}",
                body=f"Due {task.due_date}.",
                link="/app/tasks",
                severity="warning",
                resource_type="task",
                resource_id=str(task.id),
            )
        meta["overdue_notified_on"] = today.isoformat()
        task.metadata_ = meta
        emitted += 1
    await db.flush()
    return emitted


async def scan_budget_burn(db: AsyncSession) -> int:
    """Notify when posted expenses exceed 90% of budget total."""
    from decimal import Decimal

    from app.models.budget import Budget
    from app.models.finance import FinanceTransaction
    from app.services.events import emit_event

    budgets = await db.scalars(
        select(Budget).where(
            Budget.status.in_(["approved", "locked"]),
            Budget.total_amount > 0,
        )
    )
    emitted = 0
    for budget in budgets:
        spent = await db.scalar(
            select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
                FinanceTransaction.organization_id == budget.organization_id,
                FinanceTransaction.budget_id == budget.id,
                FinanceTransaction.transaction_type == "expense",
                FinanceTransaction.status == "posted",
            )
        )
        total = Decimal(str(budget.total_amount or 0))
        spent_dec = Decimal(str(spent or 0))
        if total <= 0:
            continue
        ratio = spent_dec / total
        if ratio < Decimal("0.90"):
            continue
        meta = dict(budget.metadata_ or {})
        flag = meta.get("burn_notified_ratio")
        # Re-notify only when crossing new 5% bands (90, 95, 100+)
        band = "100" if ratio >= 1 else ("95" if ratio >= Decimal("0.95") else "90")
        if flag == band:
            continue
        pct = round(float(ratio * 100), 1)
        await emit_event(
            db,
            organization_id=budget.organization_id,
            event_type=EVENT_BUDGET_BURN,
            title=f"Budget burn alert: {budget.name}",
            body=f"Spent {spent_dec} / {total} ({pct}%).",
            link="/app/budgets",
            severity="critical" if ratio >= 1 else "warning",
            resource_type="budget",
            resource_id=str(budget.id),
            role_slugs=["org_admin", "manager"],
            metadata={"ratio": pct, "band": band},
        )
        meta["burn_notified_ratio"] = band
        budget.metadata_ = meta
        emitted += 1
    await db.flush()
    return emitted


async def scan_grant_expiring(db: AsyncSession) -> int:
    """Emit ``grant.expiring`` for grants ending within 14 days (idempotent flag)."""
    from app.models.grant import Grant

    today = date.today()
    horizon = today + timedelta(days=14)
    grants = await db.scalars(
        select(Grant).where(
            Grant.end_date.is_not(None),
            Grant.end_date >= today,
            Grant.end_date <= horizon,
            Grant.status.in_(["awarded", "active"]),
        )
    )
    emitted = 0
    for grant in grants:
        meta = dict(grant.metadata_ or {})
        if meta.get("expiring_notified_on") == today.isoformat():
            continue
        await emit_event(
            db,
            organization_id=grant.organization_id,
            event_type=EVENT_GRANT_EXPIRING,
            title=f"Grant expiring soon: {grant.name}",
            body=f"Ends {grant.end_date}. Review renewal or final reporting.",
            link="/app/grants",
            severity="warning",
            resource_type="grant",
            resource_id=str(grant.id),
            role_slugs=["org_admin", "manager"],
            metadata={"end_date": str(grant.end_date)},
        )
        meta["expiring_notified_on"] = today.isoformat()
        grant.metadata_ = meta
        emitted += 1
    await db.flush()
    return emitted


async def run_job_tick() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        webhooks = await process_webhook_queue(db)
        overdue = await scan_overdue_tasks(db)
        burn = await scan_budget_burn(db)
        grants_expiring = await scan_grant_expiring(db)
        sched = await workflows.process_due_schedules(db)
        runs = await workflows.process_run_queue(db, limit=20)
        await db.commit()
        return {
            "webhooks_processed": webhooks,
            "overdue_tasks_notified": overdue,
            "budget_burn_alerts": burn,
            "grants_expiring_notified": grants_expiring,
            "workflow_schedules_enqueued": sched,
            "workflow_runs_processed": runs.get("processed", 0),
        }


async def run_job_tick_for_org(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    """Org-scoped tick used by authenticated API (webhooks only for that org)."""
    now = utcnow()
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(
            WebhookDelivery.organization_id == organization_id,
            WebhookDelivery.status == "pending",
            (WebhookDelivery.next_attempt_at.is_(None))
            | (WebhookDelivery.next_attempt_at <= now),
        )
        .order_by(WebhookDelivery.created_at.asc())
        .limit(25)
    )
    processed = 0
    for delivery in rows:
        await _deliver_one(db, delivery)
        processed += 1
    overdue = await scan_overdue_tasks(db)
    await db.flush()
    return {"webhooks_processed": processed, "overdue_tasks_notified": overdue}
