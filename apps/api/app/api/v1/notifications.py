from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, get_current_context, require_permissions
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.notification import WebhookDelivery
from app.schemas import (
    MessageResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
    PaginatedResponse,
    PaginationMeta,
    WebhookDeliveryResponse,
)
from app.services import jobs as jobs_service
from app.services import notifications as notification_service
from sqlalchemy import func, select

router = APIRouter(tags=["Notifications & Jobs"])


def _meta(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


def _require_org(ctx: RequestContext) -> UUID:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    return ctx.organization.id


@router.get("/notifications", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[NotificationResponse]:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("Notifications require a user session")
    org_id = _require_org(ctx)
    items, total = await notification_service.list_notifications(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        page=page,
        page_size=page_size,
        status=status,
    )
    return PaginatedResponse(
        items=[NotificationResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.get("/notifications/unread-count", response_model=NotificationUnreadCountResponse)
async def notifications_unread_count(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationUnreadCountResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("Notifications require a user session")
    org_id = _require_org(ctx)
    count = await notification_service.unread_count(
        db, organization_id=org_id, user_id=ctx.user.id
    )
    return NotificationUnreadCountResponse(unread_count=count)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("Notifications require a user session")
    org_id = _require_org(ctx)
    row = await notification_service.mark_read(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        notification_id=notification_id,
    )
    return NotificationResponse.model_validate(row)


@router.post("/notifications/read-all", response_model=MessageResponse)
async def mark_all_notifications_read(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("Notifications require a user session")
    org_id = _require_org(ctx)
    count = await notification_service.mark_all_read(
        db, organization_id=org_id, user_id=ctx.user.id
    )
    return MessageResponse(message=f"Marked {count} notifications as read")


@router.get(
    "/webhook-deliveries",
    response_model=PaginatedResponse[WebhookDeliveryResponse],
)
async def list_webhook_deliveries(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("integrations:read", "integrations:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[WebhookDeliveryResponse]:
    org_id = _require_org(ctx)
    filters = [WebhookDelivery.organization_id == org_id]
    if status:
        filters.append(WebhookDelivery.status == status)
    total = await db.scalar(select(func.count()).select_from(WebhookDelivery).where(*filters))
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(*filters)
        .order_by(WebhookDelivery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PaginatedResponse(
        items=[WebhookDeliveryResponse.model_validate(i) for i in rows],
        meta=_meta(page, page_size, total or 0),
    )


@router.post("/jobs/tick", response_model=dict)
async def run_jobs_tick(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("settings:update", "organizations:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Process pending webhooks and overdue-task notifications for this org."""
    org_id = _require_org(ctx)
    result = await jobs_service.run_job_tick_for_org(db, org_id)
    return {"ok": True, **result}
