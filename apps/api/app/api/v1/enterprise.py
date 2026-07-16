"""Epic 7 — Enterprise SaaS: billing, flags, domains, onboarding, SSO, backups, ops."""

from __future__ import annotations

from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import ORMModel, PaginatedResponse, PaginationMeta
from app.services import enterprise as ent

router = APIRouter(tags=["Enterprise SaaS"])

ADMIN = ("organizations:manage", "settings:update", "branding:manage")
BILLING = ("billing:read", "billing:manage", "organizations:manage")
BILLING_MANAGE = ("billing:manage", "organizations:manage")
SECURITY = ("security:manage", "organizations:manage", "settings:update")
BACKUP = ("backups:manage", "organizations:manage")
OPS = ("organizations:manage", "analytics:read")


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


class PlanResponse(ORMModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    tier: str
    billing_period: str
    price_monthly: Any
    price_annual: Any
    currency: str
    seat_limit: Optional[int] = None
    storage_gb: Optional[int] = None
    trial_days: int
    features: list = Field(default_factory=list)
    is_public: bool
    sort_order: int


class ChangePlanRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)
    billing_period: str = Field(default="monthly", max_length=16)
    seats: Optional[int] = Field(default=None, ge=1, le=100000)
    coupon_code: Optional[str] = Field(default=None, max_length=64)


class DomainCreateRequest(BaseModel):
    hostname: str = Field(min_length=3, max_length=255)
    is_primary: bool = False


class DomainResponse(ORMModel):
    id: UUID
    organization_id: UUID
    hostname: str
    is_primary: bool
    status: str
    verification_token: str
    verified_at: Optional[Any] = None
    ssl_status: str
    dns_records: list = Field(default_factory=list)
    redirect_to_primary: bool
    last_checked_at: Optional[Any] = None
    last_error: Optional[str] = None


class OnboardingUpdateRequest(BaseModel):
    step: Optional[str] = None
    complete_step: Optional[str] = None
    sector: Optional[str] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    theme_preset: Optional[str] = None
    mark_complete: bool = False


class OnboardingResponse(ORMModel):
    id: UUID
    organization_id: UUID
    status: str
    current_step: str
    checklist: dict = Field(default_factory=dict)
    sector: Optional[str] = None
    country_code: Optional[str] = None
    theme_preset: Optional[str] = None
    completed_at: Optional[Any] = None


class BackupCreateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=255)
    include: Optional[list[str]] = None


class BackupResponse(ORMModel):
    id: UUID
    organization_id: UUID
    label: str
    status: str
    backup_type: str
    size_bytes: int
    checksum: Optional[str] = None
    storage_uri: Optional[str] = None
    include: list = Field(default_factory=list)
    manifest: dict = Field(default_factory=dict)
    completed_at: Optional[Any] = None
    created_at: Any = None


class SsoUpsertRequest(BaseModel):
    provider: str = Field(default="oidc", max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    client_secret: Optional[str] = None
    enforce_sso: bool = False
    scim_enabled: bool = False
    allowed_domains: Optional[list[str]] = None


class SsoResponse(ORMModel):
    id: UUID
    organization_id: UUID
    provider: str
    status: str
    config: dict = Field(default_factory=dict)
    enforce_sso: bool
    scim_enabled: bool
    allowed_domains: list = Field(default_factory=list)
    # secrets never exposed


class OrgSettingsPatchRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class FeatureFlagResponse(ORMModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    default_enabled: bool
    rules: dict = Field(default_factory=dict)
    status: str


class LocalePackResponse(ORMModel):
    id: UUID
    locale: str
    name: str
    native_name: str
    version: str
    direction: str
    is_system: bool
    status: str
    coverage_pct: int


# -------- Billing / plans --------


@router.get("/billing/plans", response_model=PaginatedResponse[PlanResponse])
async def list_billing_plans(
    ctx: Annotated[RequestContext, Depends(require_permissions(*BILLING))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[PlanResponse]:
    _require_org(ctx)
    rows = await ent.list_plans(db, public_only=False)
    return PaginatedResponse(
        items=[PlanResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


@router.get("/public/billing/plans", response_model=PaginatedResponse[PlanResponse])
async def public_billing_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[PlanResponse]:
    """Marketing / landing page catalog — no auth."""
    rows = await ent.list_plans(db, public_only=True)
    return PaginatedResponse(
        items=[PlanResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


@router.get("/billing/subscription")
async def get_subscription(
    ctx: Annotated[RequestContext, Depends(require_permissions(*BILLING))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.models.enterprise import SubscriptionPlan

    org_id = _require_org(ctx)
    sub = await ent.get_or_create_subscription(db, org_id)
    plan = await db.get(SubscriptionPlan, sub.plan_id)
    return ent.subscription_payload(sub, plan)


class PaystackCheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)
    billing_period: str = Field(default="monthly", max_length=16)
    callback_url: Optional[str] = Field(default=None, max_length=1024)


@router.post("/billing/paystack/initialize")
async def paystack_initialize(
    body: PaystackCheckoutRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*BILLING_MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.services import paystack as paystack_service

    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    return await paystack_service.initialize_checkout(
        db,
        organization_id=org_id,
        actor=ctx.user,
        plan_code=body.plan_code,
        billing_period=body.billing_period,
        callback_url=body.callback_url,
        ip_address=ip,
        user_agent=ua,
    )


@router.get("/billing/paystack/verify")
async def paystack_verify(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*BILLING_MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    reference: str = Query(min_length=4, max_length=128),
) -> dict[str, Any]:
    from app.services import paystack as paystack_service

    _require_org(ctx)
    return await paystack_service.verify_and_activate(
        db,
        reference=reference,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
    )


@router.post("/billing/paystack/webhook")
async def paystack_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.core.config import settings
    from app.services import paystack as paystack_service

    raw = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if settings.paystack_enabled and not paystack_service.verify_webhook_signature(
        raw, signature
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid Paystack signature")
    import json

    try:
        event = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = await paystack_service.handle_webhook_event(db, event)
    await db.commit()
    return result


@router.post("/billing/subscription/change")
async def change_plan(
    body: ChangePlanRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*BILLING_MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Switch plan. Free/zero plans activate immediately.
    Paid plans use Paystack checkout when configured; otherwise internal (dev).
    """
    from app.core.config import settings
    from app.services import paystack as paystack_service

    org_id = _require_org(ctx)
    ip, ua = client_meta(request)

    # Prefer Paystack path for paid upgrades when keys are set
    if settings.paystack_enabled and body.plan_code not in {"free", "government"}:
        checkout = await paystack_service.initialize_checkout(
            db,
            organization_id=org_id,
            actor=ctx.user,
            plan_code=body.plan_code,
            billing_period=body.billing_period,
            ip_address=ip,
            user_agent=ua,
        )
        if checkout.get("mode") == "checkout":
            return checkout

    sub = await ent.change_subscription(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        plan_code=body.plan_code,
        billing_period=body.billing_period,
        seats=body.seats,
        coupon_code=body.coupon_code,
        ip_address=ip,
        user_agent=ua,
    )
    from app.models.enterprise import SubscriptionPlan

    plan = await db.get(SubscriptionPlan, sub.plan_id)
    return ent.subscription_payload(sub, plan)


# -------- Feature flags --------


@router.get("/features")
async def get_features(
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:read", "settings:read", *BILLING))],
    db: Annotated[AsyncSession, Depends(get_db)],
    environment: str = Query(default="production"),
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    features = await ent.resolve_features(
        db,
        organization_id=org_id,
        role_slugs=list(ctx.roles) or None,
        environment=environment,
    )
    return {"features": features, "environment": environment}


@router.get("/feature-flags", response_model=PaginatedResponse[FeatureFlagResponse])
async def list_feature_flags(
    ctx: Annotated[RequestContext, Depends(require_permissions(*ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[FeatureFlagResponse]:
    _require_org(ctx)
    rows = await ent.list_flags(db)
    return PaginatedResponse(
        items=[FeatureFlagResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


# -------- Domains --------


@router.get("/domains", response_model=PaginatedResponse[DomainResponse])
async def list_org_domains(
    ctx: Annotated[RequestContext, Depends(require_permissions("branding:read", *ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[DomainResponse]:
    org_id = _require_org(ctx)
    rows = await ent.list_domains(db, org_id)
    return PaginatedResponse(
        items=[DomainResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


@router.post("/domains", response_model=DomainResponse, status_code=201)
async def create_domain(
    body: DomainCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("branding:manage", *ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DomainResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ent.add_domain(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        hostname=body.hostname,
        is_primary=body.is_primary,
        ip_address=ip,
        user_agent=ua,
    )
    return DomainResponse.model_validate(row)


@router.post("/domains/{domain_id}/verify", response_model=DomainResponse)
async def verify_org_domain(
    domain_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("branding:manage", *ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DomainResponse:
    org_id = _require_org(ctx)
    row = await ent.verify_domain(db, org_id, domain_id, simulate=True)
    return DomainResponse.model_validate(row)


@router.get("/public/branding-by-host")
async def public_branding_by_host(
    db: Annotated[AsyncSession, Depends(get_db)],
    host: str = Query(min_length=1, max_length=255),
) -> dict[str, Any]:
    payload = await ent.public_branding_by_host(db, host)
    if not payload:
        raise NotFoundError("No branding for host")
    return payload


# -------- Onboarding --------


@router.get("/onboarding", response_model=OnboardingResponse)
async def get_onboarding(
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:read", "settings:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingResponse:
    org_id = _require_org(ctx)
    row = await ent.get_or_create_onboarding(db, org_id)
    return OnboardingResponse.model_validate(row)


@router.patch("/onboarding", response_model=OnboardingResponse)
async def patch_onboarding(
    body: OnboardingUpdateRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:update", *ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingResponse:
    org_id = _require_org(ctx)
    row = await ent.update_onboarding(
        db,
        org_id,
        step=body.step,
        complete_step=body.complete_step,
        sector=body.sector,
        country_code=body.country_code,
        theme_preset=body.theme_preset,
        mark_complete=body.mark_complete,
    )
    return OnboardingResponse.model_validate(row)


@router.get("/onboarding/theme-presets")
async def theme_presets(
    ctx: Annotated[RequestContext, Depends(require_permissions("branding:read", "organizations:read"))],
) -> dict[str, Any]:
    _require_org(ctx)
    return {"items": ent.THEME_PRESETS}


# -------- Tenant admin settings --------


@router.patch("/admin/settings")
async def patch_admin_settings(
    body: OrgSettingsPatchRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    org = await ent.update_org_settings(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        settings_patch=body.settings,
        ip_address=ip,
        user_agent=ua,
    )
    return {"id": str(org.id), "settings": org.settings or {}}


# -------- Backups --------


@router.get("/backups", response_model=PaginatedResponse[BackupResponse])
async def list_tenant_backups(
    ctx: Annotated[RequestContext, Depends(require_permissions(*BACKUP))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[BackupResponse]:
    org_id = _require_org(ctx)
    rows = await ent.list_backups(db, org_id)
    return PaginatedResponse(
        items=[BackupResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


@router.post("/backups", response_model=BackupResponse, status_code=201)
async def create_tenant_backup(
    body: BackupCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*BACKUP))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackupResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ent.create_backup(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        label=body.label,
        include=body.include,
        ip_address=ip,
        user_agent=ua,
    )
    return BackupResponse.model_validate(row)


@router.get("/backups/export")
async def export_all_data(
    ctx: Annotated[RequestContext, Depends(require_permissions(*BACKUP))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await ent.export_tenant_data(db, org_id)


# -------- SSO --------


@router.get("/sso", response_model=PaginatedResponse[SsoResponse])
async def list_sso(
    ctx: Annotated[RequestContext, Depends(require_permissions(*SECURITY))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[SsoResponse]:
    org_id = _require_org(ctx)
    rows = await ent.get_sso(db, org_id)
    return PaginatedResponse(
        items=[SsoResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


@router.put("/sso", response_model=SsoResponse)
async def upsert_sso_config(
    body: SsoUpsertRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SECURITY))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SsoResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ent.upsert_sso(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        provider=body.provider,
        config=body.config,
        client_secret=body.client_secret,
        enforce_sso=body.enforce_sso,
        scim_enabled=body.scim_enabled,
        allowed_domains=body.allowed_domains,
        ip_address=ip,
        user_agent=ua,
    )
    return SsoResponse.model_validate(row)


# -------- Localization --------


@router.get("/locales", response_model=PaginatedResponse[LocalePackResponse])
async def list_locale_packs(
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:read", "settings:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[LocalePackResponse]:
    _require_org(ctx)
    rows = await ent.list_locales(db)
    return PaginatedResponse(
        items=[LocalePackResponse.model_validate(r) for r in rows],
        meta=_meta(1, len(rows) or 1, len(rows)),
    )


# -------- Customer success & observability --------


@router.get("/customer-success")
async def customer_success(
    ctx: Annotated[RequestContext, Depends(require_permissions(*OPS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await ent.customer_success_metrics(db, org_id)


@router.get("/ops/observability")
async def ops_observability(
    ctx: Annotated[RequestContext, Depends(require_permissions(*OPS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    _require_org(ctx)
    return await ent.platform_observability(db)


@router.get("/plugin-sdk/manifest")
async def plugin_sdk_manifest(
    ctx: Annotated[RequestContext, Depends(require_permissions("marketplace:read", "integrations:read"))],
) -> dict[str, Any]:
    """Extension SDK contract — plugins register capabilities without modifying core."""
    _require_org(ctx)
    from app.plugins.sdk import PLUGIN_SDK_MANIFEST

    return PLUGIN_SDK_MANIFEST
