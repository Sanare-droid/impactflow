"""Epic 6 — Integrations Hub service (extends platform integrations + webhooks)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.base import utcnow
from app.models.integration_hub import (
    ConnectorSyncJob,
    FieldMappingProfile,
    PluginManifest,
)
from app.models.notification import WebhookDelivery
from app.models.platform import IntegrationConnection, OrgApiKey
from app.services.audit import write_audit_log
from app.services.connectors import CONNECTOR_CATALOG, get_connector
from app.services.connectors import runtime as connector_runtime
from app.services.programs import make_code, _ensure_unique_code
from app.services import platform as platform_service


# Standardized platform event catalog for the event bus / developer docs
STANDARD_EVENTS: list[dict[str, str]] = [
    {"code": "beneficiary.created", "description": "Beneficiary registered"},
    {"code": "beneficiary.updated", "description": "Beneficiary updated"},
    {"code": "survey.completed", "description": "Survey response submitted"},
    {"code": "survey.published", "description": "Survey published"},
    {"code": "project.completed", "description": "Project marked completed"},
    {"code": "grant.expiring", "description": "Grant approaching end date"},
    {"code": "budget.burn", "description": "Budget burn threshold exceeded"},
    {"code": "workflow.executed", "description": "Workflow run completed"},
    {"code": "report.published", "description": "Report published"},
    {"code": "prediction.opened", "description": "AI risk prediction opened"},
    {"code": "integration.failed", "description": "Integration sync or delivery failed"},
    {"code": "integration.error", "description": "Integration delivery error"},
    {"code": "device.synced", "description": "Field device sync completed"},
    {"code": "task.overdue", "description": "Task past due date"},
    {"code": "user.invited", "description": "User invited to organization"},
    {"code": "webhook.received", "description": "Inbound webhook accepted"},
    {"code": "connector.synced", "description": "Connector sync job finished"},
]


async def enable_connector(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    connector_code: str,
    name: Optional[str] = None,
    config: Optional[dict] = None,
    secret: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    events: Optional[list] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IntegrationConnection:
    connector = get_connector(connector_code)
    if not connector:
        raise NotFoundError("Connector not found")

    direction = (connector.get("directions") or ["outbound"])[0]
    safe_config = connector_runtime.store_encrypted_config(config or {}, secret=secret)
    if endpoint_url:
        pass
    elif safe_config.get("webhook_url") or (config or {}).get("webhook_url"):
        # webhook_url may be encrypted — keep endpoint on row for delivery
        revealed = connector_runtime.reveal_config_secrets(safe_config)
        endpoint_url = endpoint_url or revealed.get("webhook_url") or (config or {}).get("endpoint_url")

    # If webhook_url was passed in plaintext config before encrypt, capture endpoint
    if not endpoint_url and config and config.get("webhook_url"):
        endpoint_url = config["webhook_url"]
    if not endpoint_url and config and config.get("endpoint_url"):
        endpoint_url = config["endpoint_url"]

    data = {
        "name": name or connector["name"],
        "provider": connector_code,
        "status": "active",
        "direction": direction if direction != "inbound" else "inbound",
        "endpoint_url": endpoint_url,
        "config": safe_config,
        "events": events or [],
    }
    # Re-use platform create but secrets already encrypted in config
    row = IntegrationConnection(
        organization_id=organization_id,
        name=data["name"],
        provider=data["provider"],
        status=data["status"],
        direction=data["direction"],
        endpoint_url=data.get("endpoint_url"),
        secret_hint=(str(secret)[-4:] if secret else None),
        config=safe_config,
        events=data.get("events") or [],
        created_by_id=actor_id,
        metadata_={"connector_version": connector.get("version"), "category": connector.get("category")},
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="connectors.enable",
        resource_type="integration_connection",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Enabled connector {connector_code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def list_sync_jobs(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    integration_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> tuple[list[ConnectorSyncJob], int]:
    filters = [ConnectorSyncJob.organization_id == organization_id]
    if integration_id:
        filters.append(ConnectorSyncJob.integration_id == integration_id)
    if status:
        filters.append(ConnectorSyncJob.status == status)
    total = await db.scalar(select(func.count()).select_from(ConnectorSyncJob).where(*filters)) or 0
    rows = await db.scalars(
        select(ConnectorSyncJob)
        .where(*filters)
        .order_by(ConnectorSyncJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def create_mapping_profile(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FieldMappingProfile:
    code = await _ensure_unique_code(
        db,
        model=FieldMappingProfile,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="MAP-"),
    )
    row = FieldMappingProfile(
        organization_id=organization_id,
        integration_id=data.get("integration_id"),
        name=data["name"].strip(),
        code=code,
        entity_type=data.get("entity_type") or "beneficiary",
        connector_code=data.get("connector_code"),
        mappings=data.get("mappings") or [],
        transformations=data.get("transformations") or {},
        defaults=data.get("defaults") or {},
        validation_rules=data.get("validation_rules") or [],
        is_template=bool(data.get("is_template", False)),
        status=data.get("status") or "active",
        created_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="field_mappings.create",
        resource_type="field_mapping_profile",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created mapping profile {row.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def list_mapping_profiles(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    entity_type: Optional[str] = None,
) -> tuple[list[FieldMappingProfile], int]:
    filters = [FieldMappingProfile.organization_id == organization_id]
    if entity_type:
        filters.append(FieldMappingProfile.entity_type == entity_type)
    total = await db.scalar(select(func.count()).select_from(FieldMappingProfile).where(*filters)) or 0
    rows = await db.scalars(
        select(FieldMappingProfile)
        .where(*filters)
        .order_by(FieldMappingProfile.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


def preview_mapping(profile: FieldMappingProfile, sample: dict[str, Any]) -> dict[str, Any]:
    """Apply field mappings to a sample external payload."""
    mapped: dict[str, Any] = dict(profile.defaults or {})
    for rule in profile.mappings or []:
        source = rule.get("source")
        target = rule.get("target")
        if not source or not target:
            continue
        value = sample.get(source)
        transform = (profile.transformations or {}).get(target) or rule.get("transform")
        if transform == "lower" and isinstance(value, str):
            value = value.lower()
        elif transform == "upper" and isinstance(value, str):
            value = value.upper()
        elif transform == "trim" and isinstance(value, str):
            value = value.strip()
        if value is not None:
            mapped[target] = value
    errors = []
    for rule in profile.validation_rules or []:
        field = rule.get("field")
        if rule.get("required") and not mapped.get(field):
            errors.append(f"Required field missing: {field}")
    return {"mapped": mapped, "errors": errors, "valid": len(errors) == 0}


async def redrive_dead_webhooks(
    db: AsyncSession,
    organization_id: UUID,
    *,
    limit: int = 25,
) -> int:
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(
            WebhookDelivery.organization_id == organization_id,
            WebhookDelivery.status == "dead",
        )
        .order_by(WebhookDelivery.created_at.asc())
        .limit(limit)
    )
    count = 0
    for row in rows:
        row.status = "pending"
        row.next_attempt_at = utcnow()
        row.attempt_count = 0
        row.last_error = None
        count += 1
    await db.flush()
    return count


async def integration_monitoring(
    db: AsyncSession, organization_id: UUID
) -> dict[str, Any]:
    integrations = (
        await db.scalar(
            select(func.count())
            .select_from(IntegrationConnection)
            .where(
                IntegrationConnection.organization_id == organization_id,
                IntegrationConnection.status != "archived",
            )
        )
        or 0
    )
    healthy = (
        await db.scalar(
            select(func.count())
            .select_from(IntegrationConnection)
            .where(
                IntegrationConnection.organization_id == organization_id,
                IntegrationConnection.status == "active",
            )
        )
        or 0
    )
    errored = (
        await db.scalar(
            select(func.count())
            .select_from(IntegrationConnection)
            .where(
                IntegrationConnection.organization_id == organization_id,
                IntegrationConnection.status == "error",
            )
        )
        or 0
    )
    pending = (
        await db.scalar(
            select(func.count())
            .select_from(WebhookDelivery)
            .where(
                WebhookDelivery.organization_id == organization_id,
                WebhookDelivery.status == "pending",
            )
        )
        or 0
    )
    delivered = (
        await db.scalar(
            select(func.count())
            .select_from(WebhookDelivery)
            .where(
                WebhookDelivery.organization_id == organization_id,
                WebhookDelivery.status == "delivered",
            )
        )
        or 0
    )
    dead = (
        await db.scalar(
            select(func.count())
            .select_from(WebhookDelivery)
            .where(
                WebhookDelivery.organization_id == organization_id,
                WebhookDelivery.status == "dead",
            )
        )
        or 0
    )
    sync_failed = (
        await db.scalar(
            select(func.count())
            .select_from(ConnectorSyncJob)
            .where(
                ConnectorSyncJob.organization_id == organization_id,
                ConnectorSyncJob.status == "failed",
            )
        )
        or 0
    )
    sync_ok = (
        await db.scalar(
            select(func.count())
            .select_from(ConnectorSyncJob)
            .where(
                ConnectorSyncJob.organization_id == organization_id,
                ConnectorSyncJob.status == "completed",
            )
        )
        or 0
    )
    api_keys = (
        await db.scalar(
            select(func.count())
            .select_from(OrgApiKey)
            .where(OrgApiKey.organization_id == organization_id, OrgApiKey.status == "active")
        )
        or 0
    )
    total_wh = delivered + dead + pending
    success_rate = round((delivered / total_wh) * 100, 1) if total_wh else 100.0
    return {
        "connected_systems": integrations,
        "healthy_connectors": healthy,
        "errored_connectors": errored,
        "webhook_pending": pending,
        "webhook_delivered": delivered,
        "webhook_dead": dead,
        "queue_depth": pending,
        "sync_completed": sync_ok,
        "sync_failed": sync_failed,
        "api_keys_active": api_keys,
        "success_rate": success_rate,
        "failure_rate": round(100.0 - success_rate, 1) if total_wh else 0.0,
        "generated_at": utcnow().isoformat(),
    }


async def ensure_system_plugins(db: AsyncSession) -> None:
    seeds = [
        {
            "code": "connector-framework",
            "name": "Connector Framework",
            "version": "1.0.0",
            "events": [e["code"] for e in STANDARD_EVENTS],
            "workflow_actions": ["call_webhook", "send_slack_message"],
            "ai_tools": [],
            "description": "Core connector + event bus extension points",
        },
        {
            "code": "marketplace-foundation",
            "name": "Marketplace Foundation",
            "version": "1.0.0",
            "ui_panels": ["marketplace", "integrations_gallery"],
            "reports": [],
            "dashboards": ["integration_monitoring"],
            "description": "Install connectors, workflow packs, and report templates",
        },
    ]
    for item in seeds:
        exists = await db.scalar(
            select(PluginManifest.id).where(
                PluginManifest.code == item["code"],
                PluginManifest.version == item["version"],
                PluginManifest.organization_id.is_(None),
            )
        )
        if exists:
            continue
        db.add(
            PluginManifest(
                organization_id=None,
                code=item["code"],
                name=item["name"],
                version=item["version"],
                status="available",
                routes=item.get("routes") or [],
                events=item.get("events") or [],
                ui_panels=item.get("ui_panels") or [],
                workflow_actions=item.get("workflow_actions") or [],
                ai_tools=item.get("ai_tools") or [],
                reports=item.get("reports") or [],
                dashboards=item.get("dashboards") or [],
                mobile_features=item.get("mobile_features") or [],
                description=item.get("description"),
            )
        )
    await db.flush()


async def list_plugins(db: AsyncSession, organization_id: UUID) -> list[PluginManifest]:
    await ensure_system_plugins(db)
    rows = await db.scalars(
        select(PluginManifest).where(
            (PluginManifest.organization_id.is_(None))
            | (PluginManifest.organization_id == organization_id)
        ).order_by(PluginManifest.name.asc())
    )
    return list(rows.all())


async def clone_integration_config(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    integration_id: UUID,
    name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IntegrationConnection:
    source = await platform_service.get_integration(db, organization_id, integration_id)
    # Do not copy encrypted secrets — clone structure only
    config = {k: v for k, v in (source.config or {}).items() if k != "_encrypted"}
    config["has_secret"] = False
    row = IntegrationConnection(
        organization_id=organization_id,
        name=name or f"{source.name} (copy)",
        provider=source.provider,
        status="paused",
        direction=source.direction,
        endpoint_url=source.endpoint_url,
        secret_hint=None,
        config=config,
        events=list(source.events or []),
        created_by_id=actor_id,
        metadata_={"cloned_from": str(source.id)},
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="integrations.clone",
        resource_type="integration_connection",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Cloned integration from {source.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


def export_integration_settings(integration: IntegrationConnection) -> dict[str, Any]:
    return {
        "name": integration.name,
        "provider": integration.provider,
        "direction": integration.direction,
        "endpoint_url": integration.endpoint_url,
        "events": integration.events,
        "config": connector_runtime.redact_config_for_api(integration.config or {}),
        "metadata": integration.metadata_,
        "exported_at": utcnow().isoformat(),
    }


async def rotate_api_key(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    api_key_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    """Revoke existing key and create a replacement with the same scopes."""
    old = await db.scalar(
        select(OrgApiKey).where(
            OrgApiKey.id == api_key_id,
            OrgApiKey.organization_id == organization_id,
        )
    )
    if not old:
        raise NotFoundError("API key not found")
    scopes = list(old.scopes or ["read"])
    name = old.name
    await platform_service.revoke_api_key(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        key_id=api_key_id,
        ip=ip_address,
        user_agent=user_agent,
    )
    row, secret = await platform_service.create_api_key(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        name=name,
        scopes=scopes,
        ip=ip_address,
        user_agent=user_agent,
    )
    await write_audit_log(
        db,
        action="api_keys.rotate",
        resource_type="org_api_key",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Rotated API key {name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {
        "id": str(row.id),
        "name": row.name,
        "key_prefix": row.key_prefix,
        "scopes": row.scopes,
        "secret": secret,
        "status": row.status,
    }


def developer_portal_payload(*, api_version: str) -> dict[str, Any]:
    return {
        "api_version": api_version,
        "openapi_url": "/openapi.json",
        "docs_url": "/docs",
        "authentication": {
            "jwt": "Authorization: Bearer <access_token>",
            "api_key": "X-Api-Key: if_… or Authorization: Bearer if_…",
            "organization_header": "X-Organization-Id: <uuid>",
        },
        "webhooks": {
            "outbound": "Configure Integrations → Webhook Producer / Slack",
            "inbound": "POST /api/v1/webhooks/inbound/{path_token}",
            "signing_header": "X-ImpactFlow-Signature: sha256=…",
            "retry": "Exponential backoff; dead-letter after max attempts; redrive supported",
        },
        "events": STANDARD_EVENTS,
        "connectors": [
            {
                "code": c["code"],
                "name": c["name"],
                "category": c["category"],
                "auth_type": c["auth_type"],
                "version": c.get("version"),
                "status": c.get("status", "available"),
            }
            for c in CONNECTOR_CATALOG
        ],
        "code_samples": {
            "curl_list_beneficiaries": (
                'curl -H "Authorization: Bearer $TOKEN" '
                '-H "X-Organization-Id: $ORG" '
                "https://api.example.com/api/v1/beneficiaries"
            ),
            "curl_api_key": (
                'curl -H "X-Api-Key: if_…" '
                '-H "X-Organization-Id: $ORG" '
                "https://api.example.com/api/v1/programs"
            ),
        },
        "postman": {
            "hint": "Import OpenAPI from /openapi.json into Postman",
        },
        "changelog": [
            {"version": "0.18.0", "notes": "Epic 6 Integrations Hub & connector framework"},
            {"version": "0.17.0", "notes": "Epic 5 Executive analytics"},
            {"version": "0.16.0", "notes": "Epic 4 Field operations"},
        ],
    }
