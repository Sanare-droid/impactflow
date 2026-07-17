from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    AnalyticsOverviewResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    EvidenceUpdateRequest,
    MapFeatureCreateRequest,
    MapFeatureResponse,
    MapLayerCreateRequest,
    MapLayerResponse,
    MapLayerUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    ReportCreateRequest,
    ReportResponse,
    ReportUpdateRequest,
    SavedDashboardCreateRequest,
    SavedDashboardResponse,
    SavedDashboardUpdateRequest,
)
from app.services import insights as insights_service

router = APIRouter(tags=["Reports & Insights"])


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


# -------- Analytics --------


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("analytics:read", "dashboard:read"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyticsOverviewResponse:
    org_id = _require_org(ctx)
    data = await insights_service.analytics_overview(db, org_id)
    return AnalyticsOverviewResponse(**data)


# -------- Reports --------


@router.get("/reports", response_model=PaginatedResponse[ReportResponse])
async def list_reports(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("reports:read", "reports:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[ReportResponse]:
    org_id = _require_org(ctx)
    items, total = await insights_service.list_reports(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        report_type=report_type,
        search=search,
    )
    return PaginatedResponse(
        items=[ReportResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def create_report(
    body: ReportCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    from app.services import enterprise as ent

    await ent.enforce_writable(db, org_id)
    report = await insights_service.create_report(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("reports:read", "reports:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    org_id = _require_org(ctx)
    report = await insights_service.get_report(db, org_id, report_id)
    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: UUID,
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("reports:read", "reports:manage", "reports:export")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("markdown", pattern="^(markdown|html)$"),
):
    from fastapi.responses import PlainTextResponse

    org_id = _require_org(ctx)
    report = await insights_service.get_report(db, org_id, report_id)
    md = insights_service.render_report_markdown(report)
    if format == "html":
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{report.name}</title></head><body>"
            f"<pre style='font-family:Georgia,serif;white-space:pre-wrap'>{md}</pre>"
            "</body></html>"
        )
        return PlainTextResponse(html, media_type="text/html; charset=utf-8")
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@router.patch("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    body: ReportUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    report = await insights_service.get_report(db, org_id, report_id)
    updated = await insights_service.update_report(
        db,
        report,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ReportResponse.model_validate(updated)


@router.delete("/reports/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    report = await insights_service.get_report(db, org_id, report_id)
    await insights_service.delete_report(
        db,
        report,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Report deleted")


# -------- Saved dashboards --------


@router.get("/saved-dashboards", response_model=PaginatedResponse[SavedDashboardResponse])
async def list_saved_dashboards(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("dashboard:read", "dashboards:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[SavedDashboardResponse]:
    org_id = _require_org(ctx)
    items, total = await insights_service.list_saved_dashboards(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[SavedDashboardResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/saved-dashboards", response_model=SavedDashboardResponse, status_code=201)
async def create_saved_dashboard(
    body: SavedDashboardCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("dashboards:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SavedDashboardResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    dashboard = await insights_service.create_saved_dashboard(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return SavedDashboardResponse.model_validate(dashboard)


@router.get("/saved-dashboards/{dashboard_id}", response_model=SavedDashboardResponse)
async def get_saved_dashboard(
    dashboard_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("dashboard:read", "dashboards:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SavedDashboardResponse:
    org_id = _require_org(ctx)
    dashboard = await insights_service.get_saved_dashboard(db, org_id, dashboard_id)
    return SavedDashboardResponse.model_validate(dashboard)


@router.patch("/saved-dashboards/{dashboard_id}", response_model=SavedDashboardResponse)
async def update_saved_dashboard(
    dashboard_id: UUID,
    body: SavedDashboardUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("dashboards:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SavedDashboardResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    dashboard = await insights_service.get_saved_dashboard(db, org_id, dashboard_id)
    updated = await insights_service.update_saved_dashboard(
        db,
        dashboard,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return SavedDashboardResponse.model_validate(updated)


@router.delete("/saved-dashboards/{dashboard_id}", response_model=MessageResponse)
async def delete_saved_dashboard(
    dashboard_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("dashboards:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    dashboard = await insights_service.get_saved_dashboard(db, org_id, dashboard_id)
    await insights_service.delete_saved_dashboard(
        db,
        dashboard,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Dashboard deleted")


# -------- Maps --------


@router.get("/map-layers", response_model=PaginatedResponse[MapLayerResponse])
async def list_map_layers(
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:read", "maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[MapLayerResponse]:
    org_id = _require_org(ctx)
    items, total = await insights_service.list_map_layers(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[MapLayerResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/map-layers", response_model=MapLayerResponse, status_code=201)
async def create_map_layer(
    body: MapLayerCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MapLayerResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    layer = await insights_service.create_map_layer(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return MapLayerResponse.model_validate(layer)


@router.get("/map-layers/{layer_id}", response_model=MapLayerResponse)
async def get_map_layer(
    layer_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:read", "maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MapLayerResponse:
    org_id = _require_org(ctx)
    layer = await insights_service.get_map_layer(db, org_id, layer_id)
    return MapLayerResponse.model_validate(layer)


@router.patch("/map-layers/{layer_id}", response_model=MapLayerResponse)
async def update_map_layer(
    layer_id: UUID,
    body: MapLayerUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MapLayerResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    layer = await insights_service.get_map_layer(db, org_id, layer_id)
    updated = await insights_service.update_map_layer(
        db,
        layer,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return MapLayerResponse.model_validate(updated)


@router.delete("/map-layers/{layer_id}", response_model=MessageResponse)
async def delete_map_layer(
    layer_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    layer = await insights_service.get_map_layer(db, org_id, layer_id)
    await insights_service.delete_map_layer(
        db,
        layer,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Map layer deleted")


@router.post(
    "/map-layers/{layer_id}/features",
    response_model=MapFeatureResponse,
    status_code=201,
)
async def add_map_feature(
    layer_id: UUID,
    body: MapFeatureCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("maps:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MapFeatureResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    layer = await insights_service.get_map_layer(db, org_id, layer_id)
    feature = await insights_service.add_map_feature(
        db,
        layer,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return MapFeatureResponse.model_validate(feature)


# -------- Evidence --------


@router.get("/evidence", response_model=PaginatedResponse[EvidenceResponse])
async def list_evidence(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("evidence:read", "evidence:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    evidence_type: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[EvidenceResponse]:
    org_id = _require_org(ctx)
    items, total = await insights_service.list_evidence(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        evidence_type=evidence_type,
        search=search,
    )
    return PaginatedResponse(
        items=[EvidenceResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/evidence", response_model=EvidenceResponse, status_code=201)
async def create_evidence(
    body: EvidenceCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evidence:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    item = await insights_service.create_evidence(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return EvidenceResponse.model_validate(item)


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("evidence:read", "evidence:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceResponse:
    org_id = _require_org(ctx)
    item = await insights_service.get_evidence(db, org_id, evidence_id)
    return EvidenceResponse.model_validate(item)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: UUID,
    body: EvidenceUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evidence:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    item = await insights_service.get_evidence(db, org_id, evidence_id)
    updated = await insights_service.update_evidence(
        db,
        item,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return EvidenceResponse.model_validate(updated)


@router.delete("/evidence/{evidence_id}", response_model=MessageResponse)
async def delete_evidence(
    evidence_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evidence:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    item = await insights_service.get_evidence(db, org_id, evidence_id)
    await insights_service.delete_evidence(
        db,
        item,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Evidence deleted")
