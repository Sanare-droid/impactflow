from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    BrandingResponse,
    BrandingUpdateRequest,
    IntegrationCreateRequest,
    IntegrationResponse,
    IntegrationUpdateRequest,
    MarketplaceAppResponse,
    MarketplaceInstallRequest,
    MarketplaceInstallationResponse,
    MarketplaceInstallationUpdateRequest,
    PaginatedResponse,
    PaginationMeta,
    PublicBrandingResponse,
)
from app.services import platform as platform_service

router = APIRouter(tags=["Marketplace & Platform"])


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


# -------- Public branding (no auth) --------


@router.get("/public/branding/{slug}", response_model=PublicBrandingResponse)
async def public_branding(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicBrandingResponse:
    data = await platform_service.public_branding_by_slug(db, slug)
    if not data:
        raise NotFoundError("Organization not found")
    return PublicBrandingResponse(**data)


# -------- Marketplace --------


@router.get("/marketplace/apps", response_model=PaginatedResponse[MarketplaceAppResponse])
async def list_marketplace_apps(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("marketplace:read", "marketplace:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured: bool = False,
) -> PaginatedResponse[MarketplaceAppResponse]:
    _require_org(ctx)
    items, total = await platform_service.list_marketplace_apps(
        db,
        page=page,
        page_size=page_size,
        category=category,
        search=search,
        featured_only=featured,
    )
    return PaginatedResponse(
        items=[MarketplaceAppResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.get(
    "/marketplace/installations",
    response_model=PaginatedResponse[MarketplaceInstallationResponse],
)
async def list_installations(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("marketplace:read", "marketplace:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[MarketplaceInstallationResponse]:
    org_id = _require_org(ctx)
    items, total = await platform_service.list_installations(
        db, org_id, page=page, page_size=page_size, status=status
    )
    return PaginatedResponse(
        items=[MarketplaceInstallationResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post(
    "/marketplace/installations",
    response_model=MarketplaceInstallationResponse,
    status_code=201,
)
async def install_app(
    body: MarketplaceInstallRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("marketplace:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MarketplaceInstallationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.install_app(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        app_id=body.app_id,
        config=body.config,
        notes=body.notes,
        ip=ip,
        user_agent=ua,
    )
    return MarketplaceInstallationResponse.model_validate(row)


@router.patch(
    "/marketplace/installations/{installation_id}",
    response_model=MarketplaceInstallationResponse,
)
async def update_installation(
    installation_id: UUID,
    body: MarketplaceInstallationUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("marketplace:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MarketplaceInstallationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.update_installation(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        installation_id=installation_id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return MarketplaceInstallationResponse.model_validate(row)


# -------- API keys --------


@router.get("/api-keys", response_model=PaginatedResponse[ApiKeyResponse])
async def list_api_keys(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("api_keys:read", "api_keys:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ApiKeyResponse]:
    org_id = _require_org(ctx)
    items, total = await platform_service.list_api_keys(
        db, org_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[ApiKeyResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("api_keys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyCreatedResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row, raw = await platform_service.create_api_key(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        name=body.name,
        scopes=body.scopes,
        expires_at=body.expires_at,
        ip=ip,
        user_agent=ua,
    )
    base = ApiKeyResponse.model_validate(row)
    return ApiKeyCreatedResponse(**base.model_dump(), secret=raw)


@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("api_keys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.revoke_api_key(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        key_id=key_id,
        ip=ip,
        user_agent=ua,
    )
    return ApiKeyResponse.model_validate(row)


# -------- Integrations --------


@router.get("/integrations", response_model=PaginatedResponse[IntegrationResponse])
async def list_integrations(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("integrations:read", "integrations:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    provider: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse[IntegrationResponse]:
    org_id = _require_org(ctx)
    items, total = await platform_service.list_integrations(
        db, org_id, page=page, page_size=page_size, provider=provider, status=status
    )
    return PaginatedResponse(
        items=[IntegrationResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/integrations", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    body: IntegrationCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("integrations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntegrationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.create_integration(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        data=body.model_dump(),
        ip=ip,
        user_agent=ua,
    )
    return IntegrationResponse.model_validate(row)


@router.patch("/integrations/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    body: IntegrationUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("integrations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntegrationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.update_integration(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        integration_id=integration_id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return IntegrationResponse.model_validate(row)


@router.post("/integrations/{integration_id}/test", response_model=IntegrationResponse)
async def test_integration(
    integration_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("integrations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntegrationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.test_integration(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        integration_id=integration_id,
        ip=ip,
        user_agent=ua,
    )
    return IntegrationResponse.model_validate(row)


# -------- White label branding --------


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("branding:read", "branding:manage", "settings:read"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BrandingResponse:
    org_id = _require_org(ctx)
    row = await platform_service.get_branding(db, org_id)
    return BrandingResponse.model_validate(row)


@router.patch("/branding", response_model=BrandingResponse)
async def update_branding(
    body: BrandingUpdateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("branding:manage", "settings:update"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BrandingResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await platform_service.update_branding(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return BrandingResponse.model_validate(row)
