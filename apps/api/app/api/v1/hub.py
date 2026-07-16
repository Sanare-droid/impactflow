"""Epic 6 — Integrations Hub API (extends platform webhooks & API keys)."""

from __future__ import annotations

import json
from typing import Annotated, Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.config import settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.db.base import utcnow
from app.db.session import get_db
from app.schemas import MessageResponse, ORMModel, PaginationMeta
from app.services import events as events_service
from app.services import integration_hub as hub
from app.services.connectors import get_connector, list_connectors
from app.services.connectors import runtime as connector_runtime
from app.services.platform import get_integration

API_VERSION = "0.19.0"

router = APIRouter(tags=["Integrations Hub"])

READ = ("integrations:read", "integrations:manage")
MANAGE = ("integrations:manage",)
API_KEYS = ("api_keys:read", "api_keys:manage")


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


class EnableConnectorRequest(BaseModel):
    connector_code: str
    name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    secret: Optional[str] = None
    endpoint_url: Optional[str] = None
    events: Optional[list[str]] = None


class SyncRequest(BaseModel):
    mode: str = Field(default="incremental", pattern="^(full|incremental|dry_run)$")
    direction: str = Field(default="pull", pattern="^(pull|push)$")
    dry_run: bool = False


class MappingCreateRequest(BaseModel):
    name: str
    code: Optional[str] = None
    entity_type: str = "beneficiary"
    connector_code: Optional[str] = None
    integration_id: Optional[UUID] = None
    mappings: list[dict[str, Any]] = Field(default_factory=list)
    transformations: Optional[dict[str, Any]] = None
    defaults: Optional[dict[str, Any]] = None
    validation_rules: Optional[list[dict[str, Any]]] = None


class MappingPreviewRequest(BaseModel):
    sample: dict[str, Any] = Field(default_factory=dict)


class OAuthStartRequest(BaseModel):
    redirect_uri: str
    connector_code: Optional[str] = None


class ImportSettingsRequest(BaseModel):
    name: str
    provider: str
    direction: Optional[str] = "outbound"
    endpoint_url: Optional[str] = None
    events: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None


class SyncJobOut(ORMModel):
    id: UUID
    organization_id: UUID
    integration_id: UUID
    connector_code: str
    status: str
    direction: str
    mode: str
    records_processed: int
    records_failed: int
    error_message: Optional[str] = None
    result: dict = Field(default_factory=dict)
    started_at: Any = None
    completed_at: Any = None
    created_at: Any = None


# -------- Connector catalog --------


@router.get("/connectors")
async def connectors_catalog(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    category: Optional[str] = None,
    include_future: bool = True,
) -> dict[str, Any]:
    _require_org(ctx)
    items = list_connectors(category=category, include_future=include_future)
    return {"items": items, "total": len(items)}


@router.get("/connectors/{code}")
async def connector_detail(
    code: str,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
) -> dict[str, Any]:
    _require_org(ctx)
    connector = get_connector(code)
    if not connector:
        raise NotFoundError("Connector not found")
    return connector


@router.post("/connectors/enable", status_code=201)
async def enable_connector(
    body: EnableConnectorRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await hub.enable_connector(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        connector_code=body.connector_code,
        name=body.name,
        config=body.config,
        secret=body.secret,
        endpoint_url=body.endpoint_url,
        events=body.events,
        ip_address=ip,
        user_agent=ua,
    )
    return {
        "id": str(row.id),
        "name": row.name,
        "provider": row.provider,
        "status": row.status,
        "direction": row.direction,
        "config": connector_runtime.redact_config_for_api(row.config or {}),
    }


# -------- Health / sync --------


@router.post("/integrations/{integration_id}/health")
async def integration_health(
    integration_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    integ = await get_integration(db, org_id, integration_id)
    return await connector_runtime.health_check_connector(db, integ)


@router.post("/integrations/{integration_id}/sync", response_model=SyncJobOut)
async def integration_sync(
    integration_id: UUID,
    body: SyncRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncJobOut:
    org_id = _require_org(ctx)
    integ = await get_integration(db, org_id, integration_id)
    dry = body.dry_run or body.mode == "dry_run"
    job = await connector_runtime.run_connector_sync(
        db,
        organization_id=org_id,
        integration=integ,
        mode=body.mode if not dry else "dry_run",
        direction=body.direction,
        actor_id=ctx.user.id,
        dry_run=dry,
    )
    await events_service.emit_event(
        db,
        organization_id=org_id,
        event_type="connector.synced",
        title=f"Connector sync: {integ.name}",
        body=f"Status {job.status} · {job.records_processed} records",
        link="/app/integrations",
        severity="success" if job.status == "completed" else "warning",
        resource_type="connector_sync_job",
        resource_id=str(job.id),
        role_slugs=["org_admin", "manager"],
        notify_in_app=False,
    )
    return SyncJobOut.model_validate(job)


@router.get("/integrations/sync-jobs")
async def list_sync_jobs(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    integration_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    items, total = await hub.list_sync_jobs(
        db, org_id, page=page, page_size=page_size, integration_id=integration_id, status=status
    )
    return {
        "items": [SyncJobOut.model_validate(i).model_dump() for i in items],
        "meta": _meta(page, page_size, total).model_dump(),
    }


@router.post("/integrations/{integration_id}/clone", status_code=201)
async def clone_integration(
    integration_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Optional[str] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await hub.clone_integration_config(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        integration_id=integration_id,
        name=name,
        ip_address=ip,
        user_agent=ua,
    )
    return {"id": str(row.id), "name": row.name, "status": row.status}


@router.get("/integrations/{integration_id}/export")
async def export_integration(
    integration_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    integ = await get_integration(db, org_id, integration_id)
    return hub.export_integration_settings(integ)


@router.post("/integrations/import", status_code=201)
async def import_integration(
    body: ImportSettingsRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await hub.enable_connector(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        connector_code=body.provider,
        name=body.name,
        config=body.config,
        endpoint_url=body.endpoint_url,
        events=body.events,
        ip_address=ip,
        user_agent=ua,
    )
    return {"id": str(row.id), "name": row.name}


@router.post("/integrations/{integration_id}/oauth/start")
async def oauth_start(
    integration_id: UUID,
    body: OAuthStartRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    integ = await get_integration(db, org_id, integration_id)
    code = body.connector_code or integ.provider
    state = f"{org_id}:{integration_id}:{uuid4().hex[:12]}"
    url = connector_runtime.build_oauth_authorize_url(
        code,
        config=integ.config or {},
        redirect_uri=body.redirect_uri,
        state=state,
    )
    meta = dict(integ.metadata_ or {})
    meta["oauth_state"] = state
    integ.metadata_ = meta
    await db.flush()
    return {"authorize_url": url, "state": state}


# -------- Field mapping --------


@router.get("/field-mappings")
async def list_mappings(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entity_type: Optional[str] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    items, total = await hub.list_mapping_profiles(
        db, org_id, page=page, page_size=page_size, entity_type=entity_type
    )
    return {
        "items": [
            {
                "id": str(i.id),
                "name": i.name,
                "code": i.code,
                "entity_type": i.entity_type,
                "connector_code": i.connector_code,
                "mappings": i.mappings,
                "defaults": i.defaults,
                "validation_rules": i.validation_rules,
                "status": i.status,
            }
            for i in items
        ],
        "meta": _meta(page, page_size, total).model_dump(),
    }


@router.post("/field-mappings", status_code=201)
async def create_mapping(
    body: MappingCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await hub.create_mapping_profile(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return {"id": str(row.id), "code": row.code, "name": row.name}


@router.post("/field-mappings/{mapping_id}/preview")
async def preview_mapping(
    mapping_id: UUID,
    body: MappingPreviewRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    from sqlalchemy import select
    from app.models.integration_hub import FieldMappingProfile

    row = await db.scalar(
        select(FieldMappingProfile).where(
            FieldMappingProfile.id == mapping_id,
            FieldMappingProfile.organization_id == org_id,
        )
    )
    if not row:
        raise NotFoundError("Mapping profile not found")
    return hub.preview_mapping(row, body.sample)


# -------- Webhooks enhance --------


@router.post("/webhooks/inbound/{path_token}")
async def inbound_webhook(
    path_token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_impactflow_signature: Annotated[Optional[str], Header()] = None,
    x_organization_id: Annotated[Optional[str], Header()] = None,
) -> dict[str, Any]:
    """Inbound webhook receiver — fans into the existing event bus."""
    from sqlalchemy import select
    from app.models.platform import IntegrationConnection

    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise AppError("Invalid JSON payload", code="VALIDATION_ERROR", status_code=400) from exc

    # Find matching inbound integration by path token in config
    rows = await db.scalars(
        select(IntegrationConnection).where(
            IntegrationConnection.status == "active",
            IntegrationConnection.direction.in_(["inbound", "bidirectional"]),
        )
    )
    match = None
    for integ in rows:
        cfg = connector_runtime.reveal_config_secrets(integ.config or {})
        if cfg.get("path_token") == path_token:
            if x_organization_id and str(integ.organization_id) != x_organization_id:
                continue
            match = integ
            break
    if not match:
        raise NotFoundError("Inbound webhook not found")

    secret = connector_runtime.signing_secret_from_config(match.config or {})
    if secret and x_impactflow_signature:
        if not connector_runtime.verify_webhook_signature(
            secret, body_bytes, x_impactflow_signature
        ):
            raise ForbiddenError("Invalid webhook signature")

    event_type = payload.get("event") or "webhook.received"
    await events_service.emit_event(
        db,
        organization_id=match.organization_id,
        event_type=event_type if event_type != "webhook.received" else "webhook.received",
        title=payload.get("title") or f"Inbound webhook ({match.name})",
        body=payload.get("body") or payload.get("message"),
        link="/app/integrations",
        severity=payload.get("severity") or "info",
        resource_type="integration_connection",
        resource_id=str(match.id),
        metadata={"path_token": path_token, "payload": payload},
        role_slugs=["org_admin", "manager"],
    )
    match.last_sync_at = utcnow()
    await db.flush()
    return {"accepted": True, "integration_id": str(match.id), "event": event_type}


@router.post("/webhooks/dead/redrive")
async def redrive_dead_letter(
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(25, ge=1, le=100),
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    count = await hub.redrive_dead_webhooks(db, org_id, limit=limit)
    return {"redriven": count}


# -------- Monitoring / developer portal / plugins --------


@router.get("/integrations/monitoring")
async def monitoring_dashboard(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await hub.integration_monitoring(db, org_id)


@router.get("/developer/portal")
async def developer_portal(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ, *API_KEYS))],
) -> dict[str, Any]:
    _require_org(ctx)
    return hub.developer_portal_payload(api_version=API_VERSION)


@router.get("/developer/openapi")
async def download_openapi(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
) -> Response:
    _require_org(ctx)
    from app.main import app as fastapi_app

    schema = fastapi_app.openapi()
    return JSONResponse(schema)


@router.get("/developer/events")
async def list_platform_events(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
) -> dict[str, Any]:
    _require_org(ctx)
    return {"items": hub.STANDARD_EVENTS}


@router.get("/plugins")
async def list_plugins(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    items = await hub.list_plugins(db, org_id)
    return {
        "items": [
            {
                "id": str(p.id),
                "code": p.code,
                "name": p.name,
                "version": p.version,
                "status": p.status,
                "events": p.events,
                "ui_panels": p.ui_panels,
                "workflow_actions": p.workflow_actions,
                "ai_tools": p.ai_tools,
                "description": p.description,
            }
            for p in items
        ]
    }


@router.post("/api-keys/{key_id}/rotate")
async def rotate_key(
    key_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("api_keys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    return await hub.rotate_api_key(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        api_key_id=key_id,
        ip_address=ip,
        user_agent=ua,
    )
