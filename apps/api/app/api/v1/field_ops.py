"""Field operations API — device registration, batch sync, and sync monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, get_current_context, require_permissions
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.schemas import MessageResponse, ORMModel, PaginatedResponse, PaginationMeta
from app.services import devices as device_service
from app.services import field_sync as sync_service

router = APIRouter(tags=["Field Operations"])

SYNC_PERMS = ("sync:push", "sync:pull", "beneficiaries:manage", "surveys:submit")
DEVICE_REGISTER = ("devices:register", "sync:push")
DEVICE_READ = ("devices:read", "devices:manage", "organizations:manage")
DEVICE_MANAGE = ("devices:manage", "organizations:manage")


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


def _require_user(ctx: RequestContext) -> UUID:
    if ctx.auth_method != "jwt" or not ctx.user:
        raise ForbiddenError("Field operations require a user session")
    return ctx.user.id


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #


class DeviceRegisterRequest(BaseModel):
    device_key: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    platform: str = Field(default="unknown", max_length=32)
    app_version: Optional[str] = Field(default=None, max_length=64)
    push_token: Optional[str] = Field(default=None, max_length=512)
    storage_bytes: Optional[int] = Field(default=None, ge=0)
    pending_uploads: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[dict[str, Any]] = None


class DeviceHeartbeatRequest(BaseModel):
    app_version: Optional[str] = Field(default=None, max_length=64)
    storage_bytes: Optional[int] = Field(default=None, ge=0)
    pending_uploads: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[dict[str, Any]] = None


class DeviceStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|deactivated|revoked)$")


class DeviceResponse(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    device_key: str
    name: str
    platform: str
    app_version: Optional[str] = None
    status: str
    last_seen_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    storage_bytes: int
    pending_uploads: int
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")


class SyncMutationItem(BaseModel):
    client_mutation_id: str = Field(min_length=8, max_length=128)
    entity_type: str = Field(max_length=64)
    op: str = Field(max_length=32)
    local_id: Optional[str] = Field(default=None, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class SyncPushRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_id: Optional[UUID] = None
    mutations: list[SyncMutationItem] = Field(default_factory=list, max_length=500)


class SyncPullRequest(BaseModel):
    since: Optional[datetime] = None
    entities: Optional[list[str]] = None
    page_size: int = Field(default=100, ge=1, le=500)


class SyncRunRequest(BaseModel):
    device_id: UUID
    client_version: Optional[str] = None
    push: Optional[SyncPushRequest] = None
    pull: Optional[SyncPullRequest] = None


class MediaUploadRequest(BaseModel):
    client_mutation_id: str = Field(min_length=8, max_length=128)
    entity_type: str = Field(max_length=64)
    entity_id: Optional[UUID] = None
    file_name: str = Field(max_length=512)
    mime_type: Optional[str] = Field(default=None, max_length=128)
    file_size: int = Field(default=0, ge=0)
    metadata: Optional[dict[str, Any]] = None


class SyncSessionResponse(ORMModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pushed_count: int
    pulled_count: int
    failed_count: int
    error_message: Optional[str] = None
    sync_token: Optional[str] = None
    client_version: Optional[str] = None


class MediaUploadResponse(ORMModel):
    id: UUID
    organization_id: UUID
    device_id: Optional[UUID] = None
    client_mutation_id: str
    entity_type: str
    entity_id: Optional[UUID] = None
    file_name: str
    mime_type: Optional[str] = None
    file_size: int
    status: str
    remote_url: Optional[str] = None
    error_message: Optional[str] = None


class FieldOpsMetricsResponse(BaseModel):
    active_devices: int
    failed_mutations: int
    sync_sessions: int
    conflicts: int


# --------------------------------------------------------------------------- #
# Device endpoints
# --------------------------------------------------------------------------- #


@router.post("/devices/register", response_model=DeviceResponse, status_code=201)
async def register_device(
    body: DeviceRegisterRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_REGISTER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceResponse:
    org_id = _require_org(ctx)
    user_id = _require_user(ctx)
    ip, ua = client_meta(request)
    device = await device_service.register_device(
        db,
        organization_id=org_id,
        user_id=user_id,
        actor_email=ctx.user.email,
        device_key=body.device_key,
        name=body.name,
        platform=body.platform,
        app_version=body.app_version,
        push_token=body.push_token,
        metadata=body.metadata,
        ip_address=ip,
        user_agent=ua,
    )
    if body.storage_bytes is not None or body.pending_uploads is not None:
        device = await device_service.heartbeat_device(
            db,
            organization_id=org_id,
            device_id=device.id,
            storage_bytes=body.storage_bytes,
            pending_uploads=body.pending_uploads,
        )
    return DeviceResponse.model_validate(device)


@router.post("/devices/{device_id}/heartbeat", response_model=DeviceResponse)
async def device_heartbeat(
    device_id: UUID,
    body: DeviceHeartbeatRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_REGISTER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceResponse:
    org_id = _require_org(ctx)
    _require_user(ctx)
    device = await device_service.heartbeat_device(
        db,
        organization_id=org_id,
        device_id=device_id,
        app_version=body.app_version,
        storage_bytes=body.storage_bytes,
        pending_uploads=body.pending_uploads,
        metadata=body.metadata,
    )
    return DeviceResponse.model_validate(device)


@router.get("/devices", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user_id: Optional[UUID] = None,
) -> PaginatedResponse[DeviceResponse]:
    org_id = _require_org(ctx)
    items, total = await device_service.list_devices(
        db, org_id, page=page, page_size=page_size, status=status, user_id=user_id
    )
    return PaginatedResponse(
        items=[DeviceResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def update_device_status(
    device_id: UUID,
    body: DeviceStatusRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    device = await device_service.update_device_status(
        db,
        organization_id=org_id,
        device_id=device_id,
        status=body.status,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return DeviceResponse.model_validate(device)


# --------------------------------------------------------------------------- #
# Sync endpoints
# --------------------------------------------------------------------------- #


@router.post("/sync/push")
async def sync_push(
    body: SyncPushRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SYNC_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    user_id = _require_user(ctx)
    ip, ua = client_meta(request)
    return await sync_service.batch_push(
        db,
        organization_id=org_id,
        user_id=user_id,
        actor_email=ctx.user.email,
        device_id=body.device_id,
        mutations=[m.model_dump() for m in body.mutations],
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/sync/pull")
async def sync_pull(
    body: SyncPullRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SYNC_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    user_id = _require_user(ctx)
    return await sync_service.delta_pull(
        db,
        organization_id=org_id,
        user_id=user_id,
        since=body.since,
        entities=body.entities,
        page_size=body.page_size,
    )


@router.post("/sync/run")
async def sync_run(
    body: SyncRunRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SYNC_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Combined push + pull in one session — primary mobile sync entry point."""
    org_id = _require_org(ctx)
    user_id = _require_user(ctx)
    ip, ua = client_meta(request)

    session = await sync_service.start_sync_session(
        db,
        organization_id=org_id,
        device_id=body.device_id,
        user_id=user_id,
        client_version=body.client_version,
    )

    push_result: dict[str, Any] = {"applied": 0, "failed": 0, "results": []}
    if body.push and body.push.mutations:
        push_result = await sync_service.batch_push(
            db,
            organization_id=org_id,
            user_id=user_id,
            actor_email=ctx.user.email,
            device_id=body.device_id,
            mutations=[m.model_dump() for m in body.push.mutations],
            ip_address=ip,
            user_agent=ua,
        )

    pull_body = body.pull or SyncPullRequest()
    pull_result = await sync_service.delta_pull(
        db,
        organization_id=org_id,
        user_id=user_id,
        since=pull_body.since,
        entities=pull_body.entities,
        page_size=pull_body.page_size,
    )

    status = "completed"
    if push_result.get("failed", 0) > 0:
        status = "partial" if push_result.get("applied", 0) > 0 else "failed"

    pulled_count = sum(
        len(pull_result.get(key, []))
        for key in ("communities", "households", "beneficiaries", "surveys", "tasks", "notifications")
    )

    await sync_service.complete_sync_session(
        db,
        session=session,
        status=status,
        pushed_count=push_result.get("applied", 0),
        pulled_count=pulled_count,
        failed_count=push_result.get("failed", 0),
    )

    return {
        "session_id": str(session.id),
        "status": status,
        "push": push_result,
        "pull": pull_result,
        "sync_token": pull_result.get("sync_token"),
    }


@router.get("/sync/sessions", response_model=PaginatedResponse[SyncSessionResponse])
async def list_sync_sessions(
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    device_id: Optional[UUID] = None,
) -> PaginatedResponse[SyncSessionResponse]:
    org_id = _require_org(ctx)
    items, total = await sync_service.list_sync_sessions(
        db, org_id, page=page, page_size=page_size, device_id=device_id
    )
    return PaginatedResponse(
        items=[SyncSessionResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.get("/field-ops/metrics", response_model=FieldOpsMetricsResponse)
async def field_ops_metrics(
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FieldOpsMetricsResponse:
    org_id = _require_org(ctx)
    metrics = await sync_service.field_ops_metrics(db, org_id)
    return FieldOpsMetricsResponse(**metrics)


@router.post("/media/uploads", response_model=MediaUploadResponse, status_code=201)
async def register_media_upload(
    body: MediaUploadRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SYNC_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: Optional[UUID] = Query(default=None),
) -> MediaUploadResponse:
    org_id = _require_org(ctx)
    row = await device_service.register_media_upload(
        db,
        organization_id=org_id,
        device_id=device_id,
        client_mutation_id=body.client_mutation_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        file_name=body.file_name,
        mime_type=body.mime_type,
        file_size=body.file_size,
        metadata=body.metadata,
    )
    return MediaUploadResponse.model_validate(row)


@router.get("/media/uploads", response_model=PaginatedResponse[MediaUploadResponse])
async def list_media_uploads(
    ctx: Annotated[RequestContext, Depends(require_permissions(*DEVICE_READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    device_id: Optional[UUID] = None,
) -> PaginatedResponse[MediaUploadResponse]:
    org_id = _require_org(ctx)
    items, total = await device_service.list_media_uploads(
        db, org_id, page=page, page_size=page_size, status=status, device_id=device_id
    )
    return PaginatedResponse(
        items=[MediaUploadResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )
