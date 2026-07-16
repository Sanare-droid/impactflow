from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.base import utcnow
from app.models.marketplace import MarketplaceApp
from app.models.marketplace_install import MarketplaceInstallation
from app.models.organization import Organization
from app.models.platform import IntegrationConnection, OrgApiKey, OrgBranding
from app.services.audit import write_audit_log

CATALOG_SEED: list[dict[str, Any]] = [
    {
        "code": "kobo-connector",
        "name": "KoboToolbox Connector",
        "category": "data_collection",
        "summary": "Sync form submissions from Kobo into monitoring and evidence.",
        "description": "Connect a Kobo project, map forms to indicators, and pull submissions on a schedule.",
        "publisher": "ImpactFlow",
        "pricing_tier": "standard",
        "is_featured": True,
        "icon_key": "clipboard",
        "config_schema": {"fields": ["server_url", "token", "project_id"]},
    },
    {
        "code": "slack-alerts",
        "name": "Slack Alerts",
        "category": "communication",
        "summary": "Push delivery and MEAL alerts into Slack channels.",
        "description": "Notify program managers when predictions open, tasks slip, or reports are published.",
        "publisher": "ImpactFlow",
        "pricing_tier": "free",
        "is_featured": True,
        "icon_key": "bell",
        "config_schema": {"fields": ["webhook_url", "channel"]},
    },
    {
        "code": "google-sheets-export",
        "name": "Google Sheets Export",
        "category": "analytics",
        "summary": "Export indicator and finance snapshots to Sheets.",
        "description": "Schedule exports of monitoring results and budget burn into a linked spreadsheet.",
        "publisher": "ImpactFlow",
        "pricing_tier": "standard",
        "is_featured": False,
        "icon_key": "table",
        "config_schema": {"fields": ["spreadsheet_id", "service_account"]},
    },
    {
        "code": "odk-central",
        "name": "ODK Central",
        "category": "data_collection",
        "summary": "Ingest ODK Central submissions for field monitoring.",
        "description": "Authenticate to ODK Central and sync form data into beneficiaries and monitoring.",
        "publisher": "ImpactFlow",
        "pricing_tier": "premium",
        "is_featured": False,
        "icon_key": "map",
        "config_schema": {"fields": ["base_url", "email", "password", "project_id"]},
    },
    {
        "code": "donor-portal-pack",
        "name": "Donor Portal Pack",
        "category": "finance",
        "summary": "Branded donor-facing narrative and finance pack.",
        "description": "Package narratives, evidence, and grant burn into a shareable donor view.",
        "publisher": "ImpactFlow",
        "pricing_tier": "premium",
        "is_featured": True,
        "icon_key": "hand-coins",
        "config_schema": {"fields": ["default_grant_id"]},
    },
]


async def ensure_marketplace_catalog(db: AsyncSession) -> None:
    for item in CATALOG_SEED:
        existing = await db.scalar(
            select(MarketplaceApp.id).where(MarketplaceApp.code == item["code"])
        )
        if existing:
            continue
        db.add(
            MarketplaceApp(
                id=uuid4(),
                name=item["name"],
                code=item["code"],
                category=item["category"],
                summary=item.get("summary"),
                description=item.get("description"),
                publisher=item.get("publisher") or "ImpactFlow",
                pricing_tier=item.get("pricing_tier") or "free",
                status="published",
                is_featured=bool(item.get("is_featured")),
                icon_key=item.get("icon_key"),
                config_schema=item.get("config_schema") or {},
            )
        )
    await db.flush()


async def phase8_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    installs = await db.scalar(
        select(func.count())
        .select_from(MarketplaceInstallation)
        .where(
            MarketplaceInstallation.organization_id == organization_id,
            MarketplaceInstallation.status == "installed",
        )
    )
    integrations = await db.scalar(
        select(func.count())
        .select_from(IntegrationConnection)
        .where(
            IntegrationConnection.organization_id == organization_id,
            IntegrationConnection.status != "archived",
        )
    )
    api_keys = await db.scalar(
        select(func.count())
        .select_from(OrgApiKey)
        .where(
            OrgApiKey.organization_id == organization_id,
            OrgApiKey.status == "active",
        )
    )
    branding_enabled = await db.scalar(
        select(func.count())
        .select_from(OrgBranding)
        .where(
            OrgBranding.organization_id == organization_id,
            OrgBranding.is_enabled.is_(True),
        )
    )
    return {
        "marketplace_installs_count": installs or 0,
        "integrations_count": integrations or 0,
        "api_keys_count": api_keys or 0,
        "branding_enabled_count": branding_enabled or 0,
    }


# -------- Marketplace --------


async def list_marketplace_apps(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
) -> tuple[list[MarketplaceApp], int]:
    await ensure_marketplace_catalog(db)
    filters = [MarketplaceApp.status == "published"]
    if category:
        filters.append(MarketplaceApp.category == category)
    if featured_only:
        filters.append(MarketplaceApp.is_featured.is_(True))
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                MarketplaceApp.name.ilike(like),
                MarketplaceApp.code.ilike(like),
                MarketplaceApp.summary.ilike(like),
            )
        )
    total = await db.scalar(select(func.count()).select_from(MarketplaceApp).where(*filters))
    rows = await db.scalars(
        select(MarketplaceApp)
        .where(*filters)
        .order_by(MarketplaceApp.is_featured.desc(), MarketplaceApp.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def get_marketplace_app(db: AsyncSession, app_id: UUID) -> MarketplaceApp:
    app = await db.get(MarketplaceApp, app_id)
    if not app or app.status != "published":
        raise NotFoundError("Marketplace app not found")
    return app


async def list_installations(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> tuple[list[MarketplaceInstallation], int]:
    filters = [MarketplaceInstallation.organization_id == organization_id]
    if status:
        filters.append(MarketplaceInstallation.status == status)
    total = await db.scalar(
        select(func.count()).select_from(MarketplaceInstallation).where(*filters)
    )
    rows = await db.scalars(
        select(MarketplaceInstallation)
        .where(*filters)
        .order_by(MarketplaceInstallation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def install_app(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    app_id: UUID,
    config: Optional[dict] = None,
    notes: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MarketplaceInstallation:
    app = await get_marketplace_app(db, app_id)
    existing = await db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.organization_id == organization_id,
            MarketplaceInstallation.app_id == app.id,
        )
    )
    if existing and existing.status == "installed":
        raise ConflictError("App already installed")
    if existing:
        existing.status = "installed"
        existing.config = config or existing.config or {}
        existing.notes = notes
        existing.installed_by_id = actor_id
        row = existing
    else:
        row = MarketplaceInstallation(
            organization_id=organization_id,
            app_id=app.id,
            status="installed",
            config=config or {},
            notes=notes,
            installed_by_id=actor_id,
        )
        db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="marketplace.install",
        resource_type="marketplace_installation",
        resource_id=str(row.id),
        description=f"Installed marketplace app '{app.code}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={"app_id": str(app.id), "code": app.code},
    )
    await db.refresh(row)
    return row


async def update_installation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    installation_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MarketplaceInstallation:
    row = await db.scalar(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.id == installation_id,
            MarketplaceInstallation.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Installation not found")
    for key, value in data.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="marketplace.installation.update",
        resource_type="marketplace_installation",
        resource_id=str(row.id),
        description="Updated marketplace installation",
        ip_address=ip,
        user_agent=user_agent,
        changes=data,
    )
    await db.refresh(row)
    return row


# -------- API keys --------


def _generate_api_key() -> tuple[str, str, str]:
    raw = f"if_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]
    return raw, prefix, hash_password(raw)


async def list_api_keys(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
) -> tuple[list[OrgApiKey], int]:
    filters = [OrgApiKey.organization_id == organization_id]
    total = await db.scalar(select(func.count()).select_from(OrgApiKey).where(*filters))
    rows = await db.scalars(
        select(OrgApiKey)
        .where(*filters)
        .order_by(OrgApiKey.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def create_api_key(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    name: str,
    scopes: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[OrgApiKey, str]:
    raw, prefix, hashed = _generate_api_key()
    row = OrgApiKey(
        organization_id=organization_id,
        name=name,
        key_prefix=prefix,
        key_hash=hashed,
        scopes=scopes or ["read"],
        expires_at=expires_at,
        created_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="api_keys.create",
        resource_type="org_api_key",
        resource_id=str(row.id),
        description=f"Created API key '{name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={"prefix": prefix, "scopes": scopes or ["read"]},
    )
    await db.refresh(row)
    return row, raw


async def revoke_api_key(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    key_id: UUID,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OrgApiKey:
    row = await db.scalar(
        select(OrgApiKey).where(
            OrgApiKey.id == key_id,
            OrgApiKey.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("API key not found")
    row.status = "revoked"
    row.revoked_at = utcnow()
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="api_keys.revoke",
        resource_type="org_api_key",
        resource_id=str(row.id),
        description=f"Revoked API key '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.refresh(row)
    return row


# -------- Integrations --------


async def list_integrations(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    provider: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[list[IntegrationConnection], int]:
    filters = [IntegrationConnection.organization_id == organization_id]
    if provider:
        filters.append(IntegrationConnection.provider == provider)
    if status:
        filters.append(IntegrationConnection.status == status)
    total = await db.scalar(
        select(func.count()).select_from(IntegrationConnection).where(*filters)
    )
    rows = await db.scalars(
        select(IntegrationConnection)
        .where(*filters)
        .order_by(IntegrationConnection.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def get_integration(
    db: AsyncSession, organization_id: UUID, integration_id: UUID
) -> IntegrationConnection:
    row = await db.scalar(
        select(IntegrationConnection).where(
            IntegrationConnection.id == integration_id,
            IntegrationConnection.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Integration not found")
    return row


async def create_integration(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IntegrationConnection:
    secret = data.pop("secret", None)
    secret_hint = None
    if secret:
        secret_hint = str(secret)[-4:]
        # Store only that a secret was set — never persist plaintext in config
        config = dict(data.get("config") or {})
        config["has_secret"] = True
        data["config"] = config
    row = IntegrationConnection(
        organization_id=organization_id,
        name=data["name"],
        provider=data.get("provider") or "webhook",
        status=data.get("status") or "active",
        direction=data.get("direction") or "outbound",
        endpoint_url=data.get("endpoint_url"),
        secret_hint=secret_hint,
        config=data.get("config") or {},
        events=data.get("events") or [],
        created_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="integrations.create",
        resource_type="integration_connection",
        resource_id=str(row.id),
        description=f"Created integration '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={"provider": row.provider},
    )
    await db.refresh(row)
    return row


async def update_integration(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    integration_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IntegrationConnection:
    row = await get_integration(db, organization_id, integration_id)
    secret = data.pop("secret", None)
    if secret:
        row.secret_hint = str(secret)[-4:]
        config = dict(data.get("config") or row.config or {})
        config["has_secret"] = True
        data["config"] = config
    for key, value in data.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="integrations.update",
        resource_type="integration_connection",
        resource_id=str(row.id),
        description=f"Updated integration '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={k: v for k, v in data.items() if k != "secret"},
    )
    await db.refresh(row)
    return row


async def test_integration(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    integration_id: UUID,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IntegrationConnection:
    """Mark a dry-run connectivity check (no outbound call without configured worker)."""
    row = await get_integration(db, organization_id, integration_id)
    if not row.endpoint_url and row.provider == "webhook":
        raise AppError("Webhook endpoint URL is required before testing")
    row.last_sync_at = utcnow()
    row.last_error = None
    row.status = "active"
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="integrations.test",
        resource_type="integration_connection",
        resource_id=str(row.id),
        description=f"Tested integration '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.refresh(row)
    return row


# -------- Branding / white label --------


async def get_branding(db: AsyncSession, organization_id: UUID) -> OrgBranding:
    row = await db.scalar(
        select(OrgBranding).where(OrgBranding.organization_id == organization_id)
    )
    if not row:
        row = OrgBranding(organization_id=organization_id)
        db.add(row)
        await db.flush()
        await db.refresh(row)
    return row


async def update_branding(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OrgBranding:
    row = await get_branding(db, organization_id)
    for key, value in data.items():
        if key == "metadata" and value is not None:
            row.metadata_ = value
        elif value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="branding.update",
        resource_type="org_branding",
        resource_id=str(row.id),
        description="Updated white-label branding",
        ip_address=ip,
        user_agent=user_agent,
        changes=data,
    )
    await db.refresh(row)
    return row


async def public_branding_by_slug(db: AsyncSession, slug: str) -> Optional[dict]:
    org = await db.scalar(select(Organization).where(Organization.slug == slug))
    if not org:
        return None
    branding = await db.scalar(
        select(OrgBranding).where(OrgBranding.organization_id == org.id)
    )
    if not branding or not branding.is_enabled:
        return {
            "organization_name": org.name,
            "organization_slug": org.slug,
            "product_name": None,
            "is_enabled": False,
            "primary_color": "#0F766E",
            "secondary_color": "#44403C",
            "logo_url": org.logo_url,
            "hide_powered_by": False,
        }
    return {
        "organization_name": org.name,
        "organization_slug": org.slug,
        "product_name": branding.product_name,
        "tagline": branding.tagline,
        "is_enabled": True,
        "primary_color": branding.primary_color,
        "secondary_color": branding.secondary_color,
        "accent_color": branding.accent_color,
        "logo_url": branding.logo_url or org.logo_url,
        "favicon_url": branding.favicon_url,
        "login_background_url": branding.login_background_url,
        "support_email": branding.support_email,
        "support_url": branding.support_url,
        "hide_powered_by": branding.hide_powered_by,
    }
