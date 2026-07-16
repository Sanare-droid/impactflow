"""Domain event fan-out: in-app notifications + webhook/Slack queue."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.notification import WebhookDelivery
from app.models.platform import IntegrationConnection
from app.services import notifications as notification_service

logger = logging.getLogger(__name__)

# Events integrations may subscribe to via `events` JSON list
EVENT_PREDICTION_OPENED = "prediction.opened"
EVENT_REPORT_PUBLISHED = "report.published"
EVENT_USER_INVITED = "user.invited"
EVENT_TASK_OVERDUE = "task.overdue"
EVENT_INTEGRATION_ERROR = "integration.error"


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def enqueue_webhooks(
    db: AsyncSession,
    *,
    organization_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> list[WebhookDelivery]:
    integrations = await db.scalars(
        select(IntegrationConnection).where(
            IntegrationConnection.organization_id == organization_id,
            IntegrationConnection.status == "active",
            IntegrationConnection.direction.in_(["outbound", "bidirectional"]),
        )
    )
    created: list[WebhookDelivery] = []
    payload_hash = _hash_payload(payload)
    for integ in integrations:
        events = list(integ.events or [])
        # Empty events list = subscribe to all platform events
        if events and event_type not in events and "*" not in events:
            continue
        if not integ.endpoint_url:
            continue
        if integ.provider not in ("webhook", "slack", "custom"):
            # Still allow if endpoint is set
            pass
        row = WebhookDelivery(
            organization_id=organization_id,
            integration_id=integ.id,
            event_type=event_type,
            status="pending",
            next_attempt_at=utcnow(),
            payload=payload,
            payload_hash=payload_hash,
            endpoint_url=integ.endpoint_url,
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return created


async def emit_event(
    db: AsyncSession,
    *,
    organization_id: UUID,
    event_type: str,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
    severity: str = "info",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    exclude_user_id: Optional[UUID] = None,
    role_slugs: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
    notify_in_app: bool = True,
    enqueue_outbound: bool = True,
) -> dict[str, Any]:
    """Create in-app notifications and queue outbound deliveries."""
    notifications = []
    if notify_in_app:
        notifications = await notification_service.notify_org_members(
            db,
            organization_id=organization_id,
            event_type=event_type,
            title=title,
            body=body,
            link=link,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            role_slugs=role_slugs,
            exclude_user_id=exclude_user_id,
            metadata=metadata,
        )

    deliveries: list[WebhookDelivery] = []
    if enqueue_outbound:
        payload = {
            "event": event_type,
            "organization_id": str(organization_id),
            "title": title,
            "body": body,
            "link": link,
            "severity": severity,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "occurred_at": utcnow().isoformat(),
            "metadata": metadata or {},
        }
        deliveries = await enqueue_webhooks(
            db,
            organization_id=organization_id,
            event_type=event_type,
            payload=payload,
        )

    # Fan the event out to the workflow engine. Never let workflow issues break
    # the core notify/webhook path.
    workflow_runs = 0
    try:
        from app.services import workflows as wf

        runs = await wf.enqueue_matching_runs(
            db,
            organization_id,
            event_type,
            {
                "event": event_type,
                "title": title,
                "body": body,
                "link": link,
                "severity": severity,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": metadata or {},
            },
        )
        workflow_runs = len(runs)
    except Exception:  # noqa: BLE001
        logger.exception("workflows.enqueue_matching_runs_failed event=%s", event_type)

    return {
        "notifications": len(notifications),
        "webhook_deliveries": len(deliveries),
        "workflow_runs": workflow_runs,
    }
