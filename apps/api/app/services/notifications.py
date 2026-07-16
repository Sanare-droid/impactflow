from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.base import utcnow
from app.models.membership import OrganizationMembership
from app.models.notification import Notification, WebhookDelivery
from app.models.role import Role


async def create_notification(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    event_type: str,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
    severity: str = "info",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Notification:
    row = Notification(
        organization_id=organization_id,
        user_id=user_id,
        event_type=event_type,
        title=title[:255],
        body=body,
        link=link,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_=metadata or {},
    )
    db.add(row)
    await db.flush()
    return row


async def notify_org_members(
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
    role_slugs: Optional[list[str]] = None,
    exclude_user_id: Optional[UUID] = None,
    metadata: Optional[dict] = None,
) -> list[Notification]:
    """Notify active members, optionally filtered by role slug."""
    filters = [
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.status == "active",
    ]
    if role_slugs:
        filters.append(Role.slug.in_(role_slugs))
    query = (
        select(OrganizationMembership.user_id)
        .join(Role, Role.id == OrganizationMembership.role_id)
        .where(*filters)
        .distinct()
    )
    user_ids = list(await db.scalars(query))
    created: list[Notification] = []
    for uid in user_ids:
        if exclude_user_id and uid == exclude_user_id:
            continue
        created.append(
            await create_notification(
                db,
                organization_id=organization_id,
                user_id=uid,
                event_type=event_type,
                title=title,
                body=body,
                link=link,
                severity=severity,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
            )
        )
    return created


async def list_notifications(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    updated_after: Optional[datetime] = None,
) -> tuple[list[Notification], int]:
    filters = [
        Notification.organization_id == organization_id,
        Notification.user_id == user_id,
        Notification.status != "archived",
    ]
    if status:
        filters.append(Notification.status == status)
    if updated_after:
        filters.append(Notification.updated_at >= updated_after)
    total = await db.scalar(select(func.count()).select_from(Notification).where(*filters))
    rows = await db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def unread_count(
    db: AsyncSession, *, organization_id: UUID, user_id: UUID
) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.status == "unread",
        )
    )
    return count or 0


async def mark_read(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    notification_id: UUID,
) -> Notification:
    row = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
    )
    if not row:
        raise NotFoundError("Notification not found")
    row.status = "read"
    row.read_at = utcnow()
    await db.flush()
    await db.refresh(row)
    return row


async def mark_all_read(
    db: AsyncSession, *, organization_id: UUID, user_id: UUID
) -> int:
    rows = await db.scalars(
        select(Notification).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.status == "unread",
        )
    )
    count = 0
    now = utcnow()
    for row in rows:
        row.status = "read"
        row.read_at = now
        count += 1
    await db.flush()
    return count


async def phase10_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    total = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.organization_id == organization_id)
    )
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == organization_id,
            Notification.status == "unread",
        )
    )
    pending = await db.scalar(
        select(func.count())
        .select_from(WebhookDelivery)
        .where(
            WebhookDelivery.organization_id == organization_id,
            WebhookDelivery.status.in_(["pending", "processing"]),
        )
    )
    failed = await db.scalar(
        select(func.count())
        .select_from(WebhookDelivery)
        .where(
            WebhookDelivery.organization_id == organization_id,
            WebhookDelivery.status.in_(["failed", "dead"]),
        )
    )
    return {
        "notifications_count": total or 0,
        "unread_notifications_count": unread or 0,
        "webhook_pending_count": pending or 0,
        "webhook_failed_count": failed or 0,
    }
