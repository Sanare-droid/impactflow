"""Epic 7 — enterprise SaaS services (billing, flags, domains, onboarding, backups).

Provider-agnostic billing: Paystack for paid upgrades; Stripe-ready fields retained.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import encrypt_secret
from app.db.base import utcnow
from app.models.enterprise import (
    FeatureFlag,
    LocalizationPack,
    OnboardingState,
    OrganizationDomain,
    OrganizationSubscription,
    SsoConfiguration,
    SubscriptionPlan,
    TenantBackup,
)
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.platform import IntegrationConnection, OrgApiKey, OrgBranding
from app.models.user import User
from app.services.audit import write_audit_log
from app.services import platform as platform_service
from app.services.beneficiaries import phase5_counts
from app.services.finance import phase3_counts
from app.services.programs import phase2_counts

PLAN_SEED: list[dict[str, Any]] = [
    {
        "code": "free",
        "name": "Free",
        "tier": "free",
        "price_monthly": 0,
        "price_annual": 0,
        "seat_limit": 3,
        "storage_gb": 1,
        "trial_days": 0,
        "features": ["surveys", "beneficiaries", "reports_basic"],
        "sort_order": 0,
        "description": "Get started — up to 3 seats, core MEAL tools",
    },
    {
        "code": "starter",
        "name": "Starter",
        "tier": "starter",
        "price_monthly": 49,
        "price_annual": 490,
        "seat_limit": 10,
        "storage_gb": 10,
        "trial_days": 14,
        "features": [
            "surveys",
            "beneficiaries",
            "reports_basic",
            "workflows",
            "ai",
            "field_ops",
        ],
        "sort_order": 1,
        "description": "Field teams + AI assist for growing NGOs",
    },
    {
        "code": "professional",
        "name": "Professional",
        "tier": "professional",
        "price_monthly": 149,
        "price_annual": 1490,
        "seat_limit": 50,
        "storage_gb": 100,
        "trial_days": 14,
        "features": [
            "surveys",
            "beneficiaries",
            "reports_basic",
            "reports_advanced",
            "workflows",
            "ai",
            "field_ops",
            "integrations",
            "marketplace",
            "executive",
            "white_label",
        ],
        "sort_order": 2,
        "description": "Integrations, white-label, and executive reporting",
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "tier": "enterprise",
        "price_monthly": 499,
        "price_annual": 4990,
        "seat_limit": None,
        "storage_gb": 1000,
        "trial_days": 30,
        "features": ["*"],
        "sort_order": 3,
        "description": "Unlimited seats, SSO, custom domains, full platform",
    },
    {
        "code": "government",
        "name": "Government",
        "tier": "government",
        "price_monthly": 0,
        "price_annual": 0,
        "seat_limit": None,
        "storage_gb": None,
        "trial_days": 0,
        "features": ["*"],
        "is_public": False,
        "sort_order": 4,
        "description": "Custom government / multilateral contract",
    },
]

FLAG_SEED: list[dict[str, Any]] = [
    {"code": "ai", "name": "AI Copilot", "default_enabled": True, "rules": {"plans": ["starter", "professional", "enterprise", "government"]}},
    {"code": "workflows", "name": "Workflow Engine", "default_enabled": True, "rules": {"plans": ["starter", "professional", "enterprise", "government"]}},
    {"code": "field_ops", "name": "Field Operations", "default_enabled": True, "rules": {"plans": ["starter", "professional", "enterprise", "government"]}},
    {"code": "integrations", "name": "Integrations Hub", "default_enabled": True, "rules": {"plans": ["professional", "enterprise", "government"]}},
    {"code": "marketplace", "name": "Marketplace", "default_enabled": True, "rules": {"plans": ["professional", "enterprise", "government"]}},
    {"code": "white_label", "name": "White Label", "default_enabled": False, "rules": {"plans": ["professional", "enterprise", "government"]}},
    {"code": "custom_domains", "name": "Custom Domains", "default_enabled": False, "rules": {"plans": ["enterprise", "government"]}},
    {"code": "reports_advanced", "name": "Advanced Reporting", "default_enabled": False, "rules": {"plans": ["professional", "enterprise", "government"]}},
    {"code": "executive", "name": "Executive Analytics", "default_enabled": True, "rules": {"plans": ["professional", "enterprise", "government"]}},
    {"code": "sso", "name": "Enterprise SSO", "default_enabled": False, "rules": {"plans": ["enterprise", "government"]}},
    {"code": "offline", "name": "Mobile Offline", "default_enabled": True, "rules": {}},
]

LOCALE_SEED: list[dict[str, Any]] = [
    {"locale": "en", "name": "English", "native_name": "English", "direction": "ltr"},
    {"locale": "fr", "name": "French", "native_name": "Français", "direction": "ltr"},
    {"locale": "es", "name": "Spanish", "native_name": "Español", "direction": "ltr"},
    {"locale": "ar", "name": "Arabic", "native_name": "العربية", "direction": "rtl"},
    {"locale": "pt", "name": "Portuguese", "native_name": "Português", "direction": "ltr"},
    {"locale": "sw", "name": "Swahili", "native_name": "Kiswahili", "direction": "ltr"},
]

ONBOARDING_STEPS = [
    "welcome",
    "organization",
    "sector",
    "theme",
    "project",
    "invite",
    "ai",
    "integrations",
    "notifications",
    "complete",
]

THEME_PRESETS = [
    {"code": "impact-teal", "name": "Impact Teal", "primary": "#0F766E", "secondary": "#44403C", "accent": "#14B8A6"},
    {"code": "ocean", "name": "Ocean", "primary": "#0369A1", "secondary": "#0F172A", "accent": "#38BDF8"},
    {"code": "forest", "name": "Forest", "primary": "#166534", "secondary": "#14532D", "accent": "#4ADE80"},
    {"code": "sunset", "name": "Sunset", "primary": "#C2410C", "secondary": "#431407", "accent": "#FB923C"},
    {"code": "violet", "name": "Violet", "primary": "#6D28D9", "secondary": "#1E1B4B", "accent": "#A78BFA"},
]


async def ensure_plans(db: AsyncSession) -> None:
    for item in PLAN_SEED:
        existing = await db.scalar(
            select(SubscriptionPlan.id).where(SubscriptionPlan.code == item["code"])
        )
        if existing:
            continue
        db.add(
            SubscriptionPlan(
                code=item["code"],
                name=item["name"],
                description=item.get("description"),
                tier=item["tier"],
                billing_period="monthly",
                price_monthly=Decimal(str(item["price_monthly"])),
                price_annual=Decimal(str(item["price_annual"])),
                seat_limit=item.get("seat_limit"),
                storage_gb=item.get("storage_gb"),
                trial_days=item.get("trial_days", 14),
                features=item.get("features") or [],
                is_public=item.get("is_public", True),
                sort_order=item.get("sort_order", 0),
            )
        )
    await db.flush()


async def ensure_flags(db: AsyncSession) -> None:
    for item in FLAG_SEED:
        existing = await db.scalar(select(FeatureFlag.id).where(FeatureFlag.code == item["code"]))
        if existing:
            continue
        db.add(
            FeatureFlag(
                code=item["code"],
                name=item["name"],
                description=item.get("description"),
                default_enabled=bool(item.get("default_enabled")),
                rules=item.get("rules") or {},
            )
        )
    await db.flush()


async def ensure_locales(db: AsyncSession) -> None:
    for item in LOCALE_SEED:
        existing = await db.scalar(
            select(LocalizationPack.id).where(
                LocalizationPack.locale == item["locale"],
                LocalizationPack.version == "1.0.0",
            )
        )
        if existing:
            continue
        db.add(
            LocalizationPack(
                locale=item["locale"],
                name=item["name"],
                native_name=item["native_name"],
                version="1.0.0",
                direction=item["direction"],
                is_system=True,
                strings={
                    "app.name": "ImpactFlow",
                    "nav.dashboard": "Dashboard",
                    "nav.programs": "Programs",
                    "common.save": "Save",
                    "common.cancel": "Cancel",
                },
            )
        )
    await db.flush()


async def list_plans(db: AsyncSession, *, public_only: bool = True) -> list[SubscriptionPlan]:
    await ensure_plans(db)
    filters = [SubscriptionPlan.status == "active"]
    if public_only:
        filters.append(SubscriptionPlan.is_public.is_(True))
    rows = await db.scalars(
        select(SubscriptionPlan).where(*filters).order_by(SubscriptionPlan.sort_order.asc())
    )
    return list(rows.all())


async def get_or_create_subscription(
    db: AsyncSession, organization_id: UUID, *, plan_code: str = "free"
) -> OrganizationSubscription:
    await ensure_plans(db)
    existing = await db.scalar(
        select(OrganizationSubscription).where(
            OrganizationSubscription.organization_id == organization_id
        )
    )
    if existing:
        return existing
    plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if not plan:
        plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "free"))
    assert plan is not None
    now = utcnow()
    trial_end = now + timedelta(days=plan.trial_days) if plan.trial_days else None
    sub = OrganizationSubscription(
        organization_id=organization_id,
        plan_id=plan.id,
        status="trialing" if plan.trial_days else "active",
        billing_period="monthly",
        seats=plan.seat_limit or 5,
        trial_ends_at=trial_end,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        provider="internal",
    )
    db.add(sub)
    await db.flush()
    return sub


async def change_subscription(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: Optional[UUID] = None,
    actor_email: str = "",
    plan_code: str,
    billing_period: str = "monthly",
    seats: Optional[int] = None,
    coupon_code: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OrganizationSubscription:
    await ensure_plans(db)
    plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if not plan:
        raise NotFoundError("Plan not found")
    sub = await get_or_create_subscription(db, organization_id)
    sub.plan_id = plan.id
    sub.billing_period = billing_period
    if seats is not None:
        sub.seats = seats
    if coupon_code:
        sub.coupon_code = coupon_code
        sub.discount_percent = 10 if coupon_code.upper().startswith("SAVE") else 0
    sub.status = "active"
    # Zero-price plans stay internal; paid keep existing provider unless unset
    price = plan.price_annual if billing_period == "annual" else plan.price_monthly
    if plan.code == "free" or Decimal(str(price or 0)) <= 0:
        sub.provider = "internal"
        sub.provider_subscription_id = None
    now = utcnow()
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=365 if billing_period == "annual" else 30)
    await db.flush()
    await write_audit_log(
        db,
        action="billing.change_plan",
        resource_type="organization_subscription",
        resource_id=sub.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Changed plan to {plan_code}",
        changes={"plan": plan_code, "billing_period": billing_period},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return sub


async def resolve_features(
    db: AsyncSession,
    *,
    organization_id: UUID,
    role_slugs: Optional[list[str]] = None,
    environment: str = "production",
) -> dict[str, bool]:
    await ensure_flags(db)
    sub = await get_or_create_subscription(db, organization_id)
    plan = await db.get(SubscriptionPlan, sub.plan_id)
    plan_code = plan.code if plan else "free"
    plan_features = set(plan.features or []) if plan else set()
    org = await db.get(Organization, organization_id)
    org_settings = (org.settings or {}) if org else {}
    org_overrides = org_settings.get("feature_overrides") or {}
    region = (org.country_code or "").upper() if org else ""

    flags = list(
        (await db.scalars(select(FeatureFlag).where(FeatureFlag.status == "active"))).all()
    )
    result: dict[str, bool] = {}
    for flag in flags:
        enabled = flag.default_enabled
        rules = flag.rules or {}
        plans = rules.get("plans") or []
        if plans:
            enabled = plan_code in plans or "*" in plan_features
        if "*" in plan_features:
            enabled = True
        elif flag.code in plan_features:
            enabled = True
        orgs = rules.get("organizations") or []
        if orgs and str(organization_id) in orgs:
            enabled = True
        roles = rules.get("roles") or []
        if roles and role_slugs and any(r in roles for r in role_slugs):
            enabled = True
        regions = rules.get("regions") or []
        if regions and region in regions:
            enabled = True
        envs = rules.get("environments") or []
        if envs and environment not in envs:
            enabled = False
        if flag.code in org_overrides:
            enabled = bool(org_overrides[flag.code])
        result[flag.code] = enabled
    return result


async def add_domain(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    hostname: str,
    is_primary: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OrganizationDomain:
    host = hostname.strip().lower().rstrip(".")
    if not host or "." not in host:
        raise AppError("Invalid hostname", code="VALIDATION_ERROR", status_code=422)
    existing = await db.scalar(
        select(OrganizationDomain).where(OrganizationDomain.hostname == host)
    )
    if existing:
        raise ConflictError("Hostname already registered")
    token = secrets.token_urlsafe(24)
    if is_primary:
        primaries = await db.scalars(
            select(OrganizationDomain).where(
                OrganizationDomain.organization_id == organization_id,
                OrganizationDomain.is_primary.is_(True),
            )
        )
        for p in primaries:
            p.is_primary = False
    row = OrganizationDomain(
        organization_id=organization_id,
        hostname=host,
        is_primary=is_primary,
        status="pending",
        verification_token=token,
        dns_records=[
            {
                "type": "TXT",
                "name": f"_impactflow-verify.{host}",
                "value": f"impactflow-domain-verification={token}",
            },
            {"type": "CNAME", "name": host, "value": "edge.impactflow.app"},
        ],
        ssl_status="pending",
    )
    db.add(row)
    # Mirror primary onto branding.custom_domain
    if is_primary:
        branding = await platform_service.get_branding(db, organization_id)
        branding.custom_domain = host
    await db.flush()
    await write_audit_log(
        db,
        action="domains.create",
        resource_type="organization_domain",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added domain {host}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def verify_domain(
    db: AsyncSession, organization_id: UUID, domain_id: UUID, *, simulate: bool = True
) -> OrganizationDomain:
    row = await db.scalar(
        select(OrganizationDomain).where(
            OrganizationDomain.id == domain_id,
            OrganizationDomain.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Domain not found")
    row.last_checked_at = utcnow()
    # Production would check DNS TXT; simulate success for configured domains in v1
    if simulate:
        row.status = "active"
        row.verified_at = utcnow()
        row.ssl_status = "active"
        row.last_error = None
    else:
        row.status = "verifying"
    await db.flush()
    return row


async def public_branding_by_host(db: AsyncSession, hostname: str) -> Optional[dict]:
    host = hostname.strip().lower().split(":")[0]
    domain = await db.scalar(
        select(OrganizationDomain).where(
            OrganizationDomain.hostname == host,
            OrganizationDomain.status == "active",
        )
    )
    if domain:
        org = await db.get(Organization, domain.organization_id)
        if org:
            return await platform_service.public_branding_by_slug(db, org.slug)
    # Fallback: branding.custom_domain
    branding = await db.scalar(
        select(OrgBranding).where(
            OrgBranding.custom_domain == host,
            OrgBranding.is_enabled.is_(True),
        )
    )
    if branding:
        org = await db.get(Organization, branding.organization_id)
        if org:
            return await platform_service.public_branding_by_slug(db, org.slug)
    return None


async def get_or_create_onboarding(db: AsyncSession, organization_id: UUID) -> OnboardingState:
    row = await db.scalar(
        select(OnboardingState).where(OnboardingState.organization_id == organization_id)
    )
    if row:
        return row
    checklist = {step: False for step in ONBOARDING_STEPS}
    checklist["welcome"] = True
    row = OnboardingState(
        organization_id=organization_id,
        status="in_progress",
        current_step="organization",
        checklist=checklist,
    )
    db.add(row)
    await db.flush()
    return row


async def update_onboarding(
    db: AsyncSession,
    organization_id: UUID,
    *,
    step: Optional[str] = None,
    complete_step: Optional[str] = None,
    sector: Optional[str] = None,
    country_code: Optional[str] = None,
    theme_preset: Optional[str] = None,
    mark_complete: bool = False,
) -> OnboardingState:
    row = await get_or_create_onboarding(db, organization_id)
    checklist = dict(row.checklist or {})
    if complete_step:
        checklist[complete_step] = True
        row.checklist = checklist
    if step:
        row.current_step = step
    if sector is not None:
        row.sector = sector
    if country_code is not None:
        row.country_code = country_code
        org = await db.get(Organization, organization_id)
        if org:
            org.country_code = country_code
    if theme_preset is not None:
        row.theme_preset = theme_preset
        preset = next((t for t in THEME_PRESETS if t["code"] == theme_preset), None)
        if preset:
            branding = await platform_service.get_branding(db, organization_id)
            branding.primary_color = preset["primary"]
            branding.secondary_color = preset["secondary"]
            branding.accent_color = preset["accent"]
            branding.is_enabled = True
            meta = dict(branding.metadata_ or {})
            meta["theme_preset"] = theme_preset
            branding.metadata_ = meta
    if mark_complete or all(checklist.get(s) for s in ONBOARDING_STEPS[:-1]):
        row.status = "completed"
        row.current_step = "complete"
        checklist["complete"] = True
        row.checklist = checklist
        row.completed_at = utcnow()
    await db.flush()
    return row


async def create_backup(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    label: Optional[str] = None,
    include: Optional[list[str]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TenantBackup:
    include = include or [
        "organization",
        "programs",
        "beneficiaries",
        "surveys",
        "reports",
        "settings",
        "branding",
    ]
    org = await db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    p2 = await phase2_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    manifest = {
        "organization": {"id": str(org.id), "slug": org.slug, "name": org.name},
        "counts": {**p2, **p5},
        "exported_at": utcnow().isoformat(),
        "include": include,
    }
    raw = json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    row = TenantBackup(
        organization_id=organization_id,
        label=label or f"Backup {utcnow().date().isoformat()}",
        status="completed",
        backup_type="full",
        size_bytes=len(raw),
        checksum=checksum,
        storage_uri=f"tenant://{organization_id}/backups/{checksum[:16]}",
        include=include,
        manifest=manifest,
        created_by_id=actor_id,
        completed_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="backups.create",
        resource_type="tenant_backup",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created tenant backup {row.label}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def export_tenant_data(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    org = await db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    branding = await platform_service.get_branding(db, organization_id)
    sub = await get_or_create_subscription(db, organization_id)
    plan = await db.get(SubscriptionPlan, sub.plan_id)
    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "locale": org.locale,
            "timezone": org.timezone,
            "country_code": org.country_code,
            "settings": org.settings,
        },
        "branding": {
            "product_name": branding.product_name,
            "primary_color": branding.primary_color,
            "secondary_color": branding.secondary_color,
            "accent_color": branding.accent_color,
            "custom_domain": branding.custom_domain,
            "is_enabled": branding.is_enabled,
            "metadata": branding.metadata_,
        },
        "subscription": {
            "plan": plan.code if plan else None,
            "status": sub.status,
            "seats": sub.seats,
        },
        "counts": {
            **(await phase2_counts(db, organization_id)),
            **(await phase3_counts(db, organization_id)),
            **(await phase5_counts(db, organization_id)),
        },
        "exported_at": utcnow().isoformat(),
    }


async def upsert_sso(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    provider: str,
    config: dict,
    client_secret: Optional[str] = None,
    enforce_sso: bool = False,
    scim_enabled: bool = False,
    allowed_domains: Optional[list] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SsoConfiguration:
    row = await db.scalar(
        select(SsoConfiguration).where(
            SsoConfiguration.organization_id == organization_id,
            SsoConfiguration.provider == provider,
        )
    )
    secrets_blob: dict = {}
    if client_secret:
        secrets_blob["client_secret"] = encrypt_secret(client_secret)
    if row:
        row.config = config
        if secrets_blob:
            row.secrets_ = {**(row.secrets_ or {}), **secrets_blob}
        row.enforce_sso = enforce_sso
        row.scim_enabled = scim_enabled
        if allowed_domains is not None:
            row.allowed_domains = allowed_domains
        row.status = "configured"
    else:
        row = SsoConfiguration(
            organization_id=organization_id,
            provider=provider,
            status="configured",
            config=config,
            secrets_=secrets_blob,
            enforce_sso=enforce_sso,
            scim_enabled=scim_enabled,
            allowed_domains=allowed_domains or [],
        )
        db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="sso.configure",
        resource_type="sso_configuration",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Configured SSO provider {provider}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def customer_success_metrics(
    db: AsyncSession, organization_id: UUID
) -> dict[str, Any]:
    members = (
        await db.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == "active",
            )
        )
        or 0
    )
    p2 = await phase2_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    integrations = (
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
    api_keys = (
        await db.scalar(
            select(func.count())
            .select_from(OrgApiKey)
            .where(OrgApiKey.organization_id == organization_id, OrgApiKey.status == "active")
        )
        or 0
    )
    onboarding = await get_or_create_onboarding(db, organization_id)
    checklist = onboarding.checklist or {}
    done = sum(1 for v in checklist.values() if v)
    total = max(len(checklist), 1)
    adoption = round((done / total) * 100, 1)

    # Health score 0-100 from adoption + activity
    activity = min(100, (p2.get("projects_count", 0) * 10) + (p5.get("beneficiaries_count", 0) * 0.1) + (integrations * 15))
    health = round(min(100, adoption * 0.4 + activity * 0.6), 1)

    recommendations = []
    if not checklist.get("invite"):
        recommendations.append({"why": "No teammates invited yet", "action": "Invite your team", "href": "/app/users"})
    if integrations == 0:
        recommendations.append({"why": "No integrations connected", "action": "Browse Integrations Hub", "href": "/app/integrations"})
    if not checklist.get("theme"):
        recommendations.append({"why": "Branding not customized", "action": "Apply a theme", "href": "/app/branding"})

    return {
        "health_score": health,
        "adoption_pct": adoption,
        "active_users": members,
        "projects": p2.get("projects_count", 0),
        "beneficiaries": p5.get("beneficiaries_count", 0),
        "integrations": integrations,
        "api_keys": api_keys,
        "onboarding_status": onboarding.status,
        "recommendations": recommendations,
        "generated_at": utcnow().isoformat(),
    }


async def list_domains(db: AsyncSession, organization_id: UUID) -> list[OrganizationDomain]:
    rows = await db.scalars(
        select(OrganizationDomain)
        .where(OrganizationDomain.organization_id == organization_id)
        .order_by(OrganizationDomain.created_at.desc())
    )
    return list(rows.all())


async def list_backups(db: AsyncSession, organization_id: UUID) -> list[TenantBackup]:
    rows = await db.scalars(
        select(TenantBackup)
        .where(TenantBackup.organization_id == organization_id)
        .order_by(TenantBackup.created_at.desc())
    )
    return list(rows.all())


async def list_flags(db: AsyncSession) -> list[FeatureFlag]:
    await ensure_flags(db)
    rows = await db.scalars(
        select(FeatureFlag).where(FeatureFlag.status == "active").order_by(FeatureFlag.code.asc())
    )
    return list(rows.all())


async def list_locales(db: AsyncSession) -> list[LocalizationPack]:
    await ensure_locales(db)
    rows = await db.scalars(
        select(LocalizationPack)
        .where(LocalizationPack.status == "available")
        .order_by(LocalizationPack.locale.asc())
    )
    return list(rows.all())


async def get_sso(
    db: AsyncSession, organization_id: UUID, provider: Optional[str] = None
) -> list[SsoConfiguration]:
    filters = [SsoConfiguration.organization_id == organization_id]
    if provider:
        filters.append(SsoConfiguration.provider == provider)
    rows = await db.scalars(select(SsoConfiguration).where(*filters))
    return list(rows.all())


def subscription_payload(sub: OrganizationSubscription, plan: Optional[SubscriptionPlan]) -> dict[str, Any]:
    return {
        "id": str(sub.id),
        "organization_id": str(sub.organization_id),
        "status": sub.status,
        "billing_period": sub.billing_period,
        "seats": sub.seats,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "current_period_start": (
            sub.current_period_start.isoformat() if sub.current_period_start else None
        ),
        "current_period_end": (
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
        "cancel_at_period_end": sub.cancel_at_period_end,
        "provider": sub.provider,
        "coupon_code": sub.coupon_code,
        "discount_percent": sub.discount_percent,
        "plan": (
            {
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.name,
                "tier": plan.tier,
                "price_monthly": float(plan.price_monthly),
                "price_annual": float(plan.price_annual),
                "currency": plan.currency,
                "seat_limit": plan.seat_limit,
                "storage_gb": plan.storage_gb,
                "features": plan.features or [],
            }
            if plan
            else None
        ),
    }


async def update_org_settings(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    settings_patch: dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Organization:
    org = await db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    merged = dict(org.settings or {})
    merged.update(settings_patch)
    org.settings = merged
    await db.flush()
    await write_audit_log(
        db,
        action="organizations.settings.update",
        resource_type="organization",
        resource_id=org.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description="Updated organization admin settings",
        changes={"settings_keys": list(settings_patch.keys())},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return org


async def platform_observability(db: AsyncSession) -> dict[str, Any]:
    """Platform-wide ops snapshot for administrators (org-scoped metrics preferred elsewhere)."""
    org_count = await db.scalar(select(func.count()).select_from(Organization)) or 0
    user_count = await db.scalar(select(func.count()).select_from(User)) or 0
    return {
        "organizations": org_count,
        "users": user_count,
        "api_health": "ok",
        "database": "ok",
        "generated_at": utcnow().isoformat(),
        "components": [
            {"name": "api", "status": "healthy"},
            {"name": "postgres", "status": "healthy"},
            {"name": "redis", "status": "healthy"},
            {"name": "workers", "status": "healthy"},
            {"name": "event_bus", "status": "healthy"},
        ],
    }
