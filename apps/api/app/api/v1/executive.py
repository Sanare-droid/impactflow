"""Epic 5 — Executive analytics, donor reporting templates, and multi-format exports."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import MessageResponse, ORMModel, PaginatedResponse, PaginationMeta, ReportResponse
from app.services import executive as exec_service
from app.services import insights as insights_service
from app.services import report_engine
from app.services import ai as ai_service

router = APIRouter(tags=["Executive Analytics & Donor Reporting"])

READ = ("analytics:read", "dashboard:read", "reports:read")
MANAGE = ("reports:manage",)
EXPORT = ("reports:export", "reports:read", "reports:manage")


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


class CloneTemplateRequest(BaseModel):
    code: Optional[str] = None
    template_id: Optional[UUID] = None
    name: Optional[str] = None


class ReportVersionCreateRequest(BaseModel):
    changelog: Optional[str] = None
    citations: Optional[list[dict[str, Any]]] = None


class ReportVersionResponse(ORMModel):
    id: UUID
    organization_id: UUID
    report_id: UUID
    version: int
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    sections: list = Field(default_factory=list)
    changelog: Optional[str] = None
    status: str
    citations: list = Field(default_factory=list)
    created_at: Any = None


class BuildReportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    template_code: Optional[str] = None
    template_id: Optional[UUID] = None
    report_type: Optional[str] = "donor"
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    grant_id: Optional[UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    generate_narrative: bool = True
    narrative_type: Optional[str] = "donor"
    save_version: bool = True


class ExecutiveBriefRequest(BaseModel):
    audience: str = Field(default="board")  # board | donor | management | government | investor
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    save_as_report: bool = True


# -------- Executive dashboard & analytics --------


@router.get("/executive/dashboard")
async def get_executive_dashboard(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await exec_service.executive_dashboard(
        db, org_id, program_id=program_id, project_id=project_id
    )


@router.get("/executive/portfolio")
async def get_portfolio_analytics(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    grant_id: Optional[UUID] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await exec_service.portfolio_analytics(
        db, org_id, program_id=program_id, project_id=project_id, grant_id=grant_id
    )


@router.get("/executive/impact")
async def get_impact_measurement(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await exec_service.impact_measurement(db, org_id)


@router.get("/executive/compliance")
async def get_compliance_dashboard(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await exec_service.compliance_dashboard(db, org_id)


@router.get("/executive/risks")
async def get_risk_intelligence(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await exec_service.risk_intelligence(db, org_id)


@router.post("/executive/briefs")
async def create_executive_brief(
    body: ExecutiveBriefRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:manage", "ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """One-click executive brief — extends existing AI generate_report (no new AI stack)."""
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    audience_map = {
        "board": "board",
        "donor": "donor",
        "management": "executive_brief",
        "government": "executive_brief",
        "investor": "executive_brief",
    }
    rtype = audience_map.get(body.audience, "executive_brief")
    generated = await ai_service.generate_report(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        report_type=rtype,
        program_id=body.program_id,
        project_id=body.project_id,
        save_narrative=True,
        permissions=list(ctx.permissions or []),
    )
    report = None
    if body.save_as_report:
        report = await insights_service.create_report(
            db,
            organization_id=org_id,
            actor_id=ctx.user.id,
            actor_email=ctx.user.email,
            data={
                "name": f"Executive Brief — {body.audience.title()}",
                "report_type": "executive_brief",
                "status": "draft",
                "program_id": body.program_id,
                "project_id": body.project_id,
                "summary": (generated.get("content") or "")[:500],
                "content": generated.get("content"),
                "sections": [
                    {"id": "highlights", "title": "Highlights"},
                    {"id": "risks", "title": "Risks"},
                    {"id": "kpis", "title": "KPIs"},
                    {"id": "decisions", "title": "Recommended Decisions"},
                ],
            },
            ip_address=ip,
            user_agent=ua,
        )
        await report_engine.create_report_version(
            db,
            report=report,
            actor_id=ctx.user.id,
            actor_email=ctx.user.email,
            changelog="Initial AI-assisted executive brief",
            citations=[{"source": "ai.generate_report", "report_type": rtype}],
            ip_address=ip,
            user_agent=ua,
        )
    return {
        "audience": body.audience,
        "narrative": generated,
        "report": ReportResponse.model_validate(report).model_dump() if report else None,
    }


# -------- Templates --------


@router.get("/report-templates")
async def list_report_templates(
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:read", "reports:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    items, total = await report_engine.list_templates(
        db, org_id, page=page, page_size=page_size, category=category
    )
    return {"items": items, "meta": _meta(page, page_size, total).model_dump()}


@router.post("/report-templates/clone", status_code=201)
async def clone_report_template(
    body: CloneTemplateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    tpl = await report_engine.clone_template(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        code=body.code,
        template_id=body.template_id,
        name=body.name,
        ip_address=ip,
        user_agent=ua,
    )
    return {
        "id": str(tpl.id),
        "name": tpl.name,
        "code": tpl.code,
        "category": tpl.category,
        "sections": tpl.sections,
    }


# -------- Report builder + versions --------


@router.post("/reports/build", response_model=ReportResponse, status_code=201)
async def build_report(
    body: BuildReportRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    """Visual report builder backend — template + optional AI narrative → Report."""
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)

    sections: list = []
    report_type = body.report_type or "donor"
    if body.template_code or body.template_id:
        if body.template_id:
            tpl = await report_engine.get_template(db, org_id, body.template_id)
            sections = list(tpl.sections or [])
            report_type = tpl.report_type or report_type
        else:
            match = next(
                (t for t in report_engine.SYSTEM_TEMPLATES if t["code"] == body.template_code),
                None,
            )
            if match:
                sections = list(match.get("sections") or [])
                report_type = match.get("report_type") or report_type

    content = None
    summary = None
    if body.generate_narrative:
        generated = await ai_service.generate_report(
            db,
            organization_id=org_id,
            actor_id=ctx.user.id,
            report_type=body.narrative_type or report_type,
            program_id=body.program_id,
            project_id=body.project_id,
            save_narrative=True,
            permissions=list(ctx.permissions or []),
        )
        content = generated.get("content")
        summary = (content or "")[:500]

    report = await insights_service.create_report(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data={
            "name": body.name,
            "report_type": report_type,
            "status": "draft",
            "program_id": body.program_id,
            "project_id": body.project_id,
            "grant_id": body.grant_id,
            "period_start": body.period_start,
            "period_end": body.period_end,
            "summary": summary,
            "content": content,
            "sections": sections,
        },
        ip_address=ip,
        user_agent=ua,
    )
    if body.save_version:
        await report_engine.create_report_version(
            db,
            report=report,
            actor_id=ctx.user.id,
            actor_email=ctx.user.email,
            changelog="Initial build from template",
            citations=[{"source": "report_engine.build", "template": body.template_code}],
            ip_address=ip,
            user_agent=ua,
        )
    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/versions", response_model=ReportVersionResponse, status_code=201)
async def create_version(
    report_id: UUID,
    body: ReportVersionCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportVersionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    report = await insights_service.get_report(db, org_id, report_id)
    ver = await report_engine.create_report_version(
        db,
        report=report,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        changelog=body.changelog,
        citations=body.citations,
        ip_address=ip,
        user_agent=ua,
    )
    return ReportVersionResponse.model_validate(ver)


@router.get("/reports/{report_id}/versions")
async def list_versions(
    report_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("reports:read", "reports:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    items = await report_engine.list_report_versions(db, org_id, report_id)
    return {"items": [ReportVersionResponse.model_validate(i).model_dump() for i in items]}


@router.post("/reports/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
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
        data={"status": "approved"},
        ip_address=ip,
        user_agent=ua,
    )
    await report_engine.create_report_version(
        db,
        report=updated,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        changelog="Approved",
        ip_address=ip,
        user_agent=ua,
    )
    return ReportResponse.model_validate(updated)


@router.post("/reports/{report_id}/publish", response_model=ReportResponse)
async def publish_report(
    report_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE))],
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
        data={"status": "published"},
        ip_address=ip,
        user_agent=ua,
    )
    await report_engine.create_report_version(
        db,
        report=updated,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        changelog="Published",
        ip_address=ip,
        user_agent=ua,
    )
    return ReportResponse.model_validate(updated)


# -------- Extended exports (reuse report markdown renderer) --------


@router.get("/reports/{report_id}/export/download")
async def export_report_download(
    report_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*EXPORT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query(
        "markdown",
        pattern="^(markdown|html|pdf|csv|xlsx|excel|docx|pptx)$",
    ),
):
    org_id = _require_org(ctx)
    report = await insights_service.get_report(db, org_id, report_id)
    payload, media_type, ext = report_engine.export_report_payload(report, format)
    filename = f"{report.code}.{ext}"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
