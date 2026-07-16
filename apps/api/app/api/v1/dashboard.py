from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.audit import AuditLog
from app.schemas import (
    AuditLogResponse,
    DashboardStatsResponse,
    OrganizationResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.services.auth import get_dashboard_stats

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    ctx: Annotated[RequestContext, Depends(require_permissions("dashboard:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardStatsResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    stats = await get_dashboard_stats(db, ctx.organization.id)
    return DashboardStatsResponse(
        users_count=stats["users_count"],
        active_memberships=stats["active_memberships"],
        roles_count=stats["roles_count"],
        recent_audit_events=stats["recent_audit_events"],
        organization=OrganizationResponse.model_validate(stats["organization"]),
        programs_count=stats["programs_count"],
        projects_count=stats["projects_count"],
        activities_count=stats["activities_count"],
        tasks_count=stats["tasks_count"],
        open_tasks_count=stats["open_tasks_count"],
        donors_count=stats["donors_count"],
        grants_count=stats["grants_count"],
        active_grants_count=stats["active_grants_count"],
        budgets_count=stats["budgets_count"],
        grants_awarded_total=stats["grants_awarded_total"],
        grants_received_total=stats["grants_received_total"],
        expenses_total=stats["expenses_total"],
        theories_of_change_count=stats["theories_of_change_count"],
        logframes_count=stats["logframes_count"],
        indicators_count=stats["indicators_count"],
        active_indicators_count=stats["active_indicators_count"],
        monitoring_results_count=stats["monitoring_results_count"],
        evaluations_count=stats["evaluations_count"],
        communities_count=stats["communities_count"],
        households_count=stats["households_count"],
        beneficiaries_count=stats["beneficiaries_count"],
        active_beneficiaries_count=stats["active_beneficiaries_count"],
        beneficiary_memberships_count=stats["beneficiary_memberships_count"],
        reports_count=stats["reports_count"],
        published_reports_count=stats["published_reports_count"],
        saved_dashboards_count=stats["saved_dashboards_count"],
        map_layers_count=stats["map_layers_count"],
        map_features_count=stats["map_features_count"],
        evidence_count=stats["evidence_count"],
        verified_evidence_count=stats["verified_evidence_count"],
    )


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    ctx: Annotated[RequestContext, Depends(require_permissions("audit:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[AuditLogResponse]:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    from sqlalchemy import func

    base = select(AuditLog).where(AuditLog.organization_id == ctx.organization.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await db.execute(
        base.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [AuditLogResponse.model_validate(row) for row in result.scalars().all()]
    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )
