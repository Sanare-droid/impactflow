from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.evidence import EvidenceItem
from app.models.map_layer import MapFeature, MapLayer
from app.models.program import Program
from app.models.project import Project
from app.models.report import Report
from app.models.saved_dashboard import SavedDashboard
from app.services.audit import write_audit_log
from app.services.beneficiaries import phase5_counts
from app.services.finance import phase3_counts
from app.services.meal import phase4_counts
from app.services.programs import make_code, _ensure_unique_code, phase2_counts


def _dec(value: Optional[Decimal | float | int | str]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


async def _assert_program(db: AsyncSession, organization_id: UUID, program_id: UUID) -> None:
    exists = await db.scalar(
        select(Program.id).where(Program.id == program_id, Program.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Program not found")


async def _assert_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> None:
    exists = await db.scalar(
        select(Project.id).where(Project.id == project_id, Project.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Project not found")


async def _assert_links(db: AsyncSession, organization_id: UUID, data: dict) -> None:
    if data.get("program_id"):
        await _assert_program(db, organization_id, data["program_id"])
    if data.get("project_id"):
        await _assert_project(db, organization_id, data["project_id"])


# -------- Reports --------


async def get_report(db: AsyncSession, organization_id: UUID, report_id: UUID) -> Report:
    report = await db.scalar(
        select(Report).where(Report.id == report_id, Report.organization_id == organization_id)
    )
    if not report:
        raise NotFoundError("Report not found")
    return report


def render_report_markdown(report: Report) -> str:
    lines = [
        f"# {report.name}",
        "",
        f"**Code:** {report.code}  ",
        f"**Type:** {report.report_type}  ",
        f"**Status:** {report.status}  ",
    ]
    if report.period_start or report.period_end:
        lines.append(
            f"**Period:** {report.period_start or '—'} → {report.period_end or '—'}  "
        )
    lines.append("")
    if report.summary:
        lines.extend(["## Summary", "", report.summary, ""])
    if report.content:
        lines.extend(["## Content", "", report.content, ""])
    lines.append(f"_Exported from ImpactFlow · {report.code}_")
    return "\n".join(lines)


async def list_reports(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Report], int]:
    filters = [Report.organization_id == organization_id]
    if status:
        filters.append(Report.status == status)
    if report_type:
        filters.append(Report.report_type == report_type)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(Report.name.ilike(like), Report.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    result = await db.execute(
        select(Report)
        .where(*filters)
        .order_by(Report.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_report(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Report:
    await _assert_links(db, organization_id, data)
    code = await _ensure_unique_code(
        db,
        model=Report,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="RPT-"),
    )
    report = Report(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        grant_id=data.get("grant_id"),
        name=data["name"].strip(),
        code=code,
        report_type=data.get("report_type") or "progress",
        status=data.get("status") or "draft",
        period_start=data.get("period_start"),
        period_end=data.get("period_end"),
        summary=data.get("summary"),
        content=data.get("content"),
        sections=data.get("sections") or [],
        created_by_id=actor_id,
    )
    db.add(report)
    await db.flush()
    await write_audit_log(
        db,
        action="reports.create",
        resource_type="report",
        resource_id=report.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created report {report.code}",
        changes={"name": report.name, "code": report.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return report


async def update_report(
    db: AsyncSession,
    report: Report,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Report:
    previous_status = report.status
    await _assert_links(db, report.organization_id, data)
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="RPT-")
        if new_code != report.code:
            data["code"] = await _ensure_unique_code(
                db, model=Report, organization_id=report.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(report, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="reports.update",
        resource_type="report",
        resource_id=report.id,
        organization_id=report.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated report {report.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if previous_status != "published" and report.status == "published":
        from app.services.events import EVENT_REPORT_PUBLISHED, emit_event

        await emit_event(
            db,
            organization_id=report.organization_id,
            event_type=EVENT_REPORT_PUBLISHED,
            title=f"Report published: {report.name}",
            body=f"{report.code} is now published.",
            link="/app/reports",
            severity="success",
            resource_type="report",
            resource_id=str(report.id),
            role_slugs=["org_admin", "manager", "meal_officer"],
        )
    return report


async def delete_report(
    db: AsyncSession,
    report: Report,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="reports.delete",
        resource_type="report",
        resource_id=report.id,
        organization_id=report.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted report {report.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(report)
    await db.flush()


# -------- Saved dashboards --------


async def get_saved_dashboard(
    db: AsyncSession, organization_id: UUID, dashboard_id: UUID
) -> SavedDashboard:
    dashboard = await db.scalar(
        select(SavedDashboard).where(
            SavedDashboard.id == dashboard_id,
            SavedDashboard.organization_id == organization_id,
        )
    )
    if not dashboard:
        raise NotFoundError("Dashboard not found")
    return dashboard


async def list_saved_dashboards(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[SavedDashboard], int]:
    filters = [SavedDashboard.organization_id == organization_id]
    if status:
        filters.append(SavedDashboard.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(SavedDashboard.name.ilike(like), SavedDashboard.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(SavedDashboard).where(*filters)) or 0
    result = await db.execute(
        select(SavedDashboard)
        .where(*filters)
        .order_by(SavedDashboard.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_saved_dashboard(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SavedDashboard:
    code = await _ensure_unique_code(
        db,
        model=SavedDashboard,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="DASH-"),
    )
    if data.get("is_default"):
        existing = await db.scalars(
            select(SavedDashboard).where(
                SavedDashboard.organization_id == organization_id,
                SavedDashboard.is_default.is_(True),
            )
        )
        for row in existing.all():
            row.is_default = False
    dashboard = SavedDashboard(
        organization_id=organization_id,
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        status=data.get("status") or "active",
        is_default=bool(data.get("is_default", False)),
        layout=data.get("layout") or {},
        widgets=data.get("widgets") or [],
        filters=data.get("filters") or {},
        created_by_id=actor_id,
    )
    db.add(dashboard)
    await db.flush()
    await write_audit_log(
        db,
        action="dashboards.create",
        resource_type="saved_dashboard",
        resource_id=dashboard.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created dashboard {dashboard.code}",
        changes={"name": dashboard.name, "code": dashboard.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return dashboard


async def update_saved_dashboard(
    db: AsyncSession,
    dashboard: SavedDashboard,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SavedDashboard:
    if data.get("is_default"):
        existing = await db.scalars(
            select(SavedDashboard).where(
                SavedDashboard.organization_id == dashboard.organization_id,
                SavedDashboard.is_default.is_(True),
                SavedDashboard.id != dashboard.id,
            )
        )
        for row in existing.all():
            row.is_default = False
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="DASH-")
        if new_code != dashboard.code:
            data["code"] = await _ensure_unique_code(
                db,
                model=SavedDashboard,
                organization_id=dashboard.organization_id,
                code=new_code,
            )
    for key, value in data.items():
        setattr(dashboard, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="dashboards.update",
        resource_type="saved_dashboard",
        resource_id=dashboard.id,
        organization_id=dashboard.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated dashboard {dashboard.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return dashboard


async def delete_saved_dashboard(
    db: AsyncSession,
    dashboard: SavedDashboard,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="dashboards.delete",
        resource_type="saved_dashboard",
        resource_id=dashboard.id,
        organization_id=dashboard.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted dashboard {dashboard.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(dashboard)
    await db.flush()


# -------- Maps --------


async def get_map_layer(db: AsyncSession, organization_id: UUID, layer_id: UUID) -> MapLayer:
    layer = await db.scalar(
        select(MapLayer)
        .options(selectinload(MapLayer.features))
        .where(MapLayer.id == layer_id, MapLayer.organization_id == organization_id)
    )
    if not layer:
        raise NotFoundError("Map layer not found")
    return layer


async def list_map_layers(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[MapLayer], int]:
    filters = [MapLayer.organization_id == organization_id]
    if status:
        filters.append(MapLayer.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(MapLayer.name.ilike(like), MapLayer.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(MapLayer).where(*filters)) or 0
    result = await db.execute(
        select(MapLayer)
        .options(selectinload(MapLayer.features))
        .where(*filters)
        .order_by(MapLayer.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def create_map_layer(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MapLayer:
    await _assert_links(db, organization_id, data)
    features_data = data.pop("features", None) or []
    code = await _ensure_unique_code(
        db,
        model=MapLayer,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="MAP-"),
    )
    layer = MapLayer(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        name=data["name"].strip(),
        code=code,
        layer_type=data.get("layer_type") or "sites",
        status=data.get("status") or "active",
        description=data.get("description"),
        style=data.get("style") or {},
        created_by_id=actor_id,
    )
    db.add(layer)
    await db.flush()
    for idx, feature in enumerate(features_data):
        db.add(
            MapFeature(
                organization_id=organization_id,
                layer_id=layer.id,
                name=feature["name"],
                feature_type=feature.get("feature_type") or "point",
                latitude=_dec(feature.get("latitude")),
                longitude=_dec(feature.get("longitude")),
                geometry=feature.get("geometry"),
                properties=feature.get("properties") or {},
                community_id=feature.get("community_id"),
                sort_order=feature.get("sort_order", idx),
            )
        )
    await db.flush()
    await write_audit_log(
        db,
        action="maps.create",
        resource_type="map_layer",
        resource_id=layer.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created map layer {layer.code}",
        changes={"name": layer.name, "code": layer.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_map_layer(db, organization_id, layer.id)


async def update_map_layer(
    db: AsyncSession,
    layer: MapLayer,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MapLayer:
    await _assert_links(db, layer.organization_id, data)
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="MAP-")
        if new_code != layer.code:
            data["code"] = await _ensure_unique_code(
                db, model=MapLayer, organization_id=layer.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(layer, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="maps.update",
        resource_type="map_layer",
        resource_id=layer.id,
        organization_id=layer.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated map layer {layer.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_map_layer(db, layer.organization_id, layer.id)


async def delete_map_layer(
    db: AsyncSession,
    layer: MapLayer,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="maps.delete",
        resource_type="map_layer",
        resource_id=layer.id,
        organization_id=layer.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted map layer {layer.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(layer)
    await db.flush()


async def add_map_feature(
    db: AsyncSession,
    layer: MapLayer,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MapFeature:
    feature = MapFeature(
        organization_id=layer.organization_id,
        layer_id=layer.id,
        name=data["name"].strip(),
        feature_type=data.get("feature_type") or "point",
        latitude=_dec(data.get("latitude")),
        longitude=_dec(data.get("longitude")),
        geometry=data.get("geometry"),
        properties=data.get("properties") or {},
        community_id=data.get("community_id"),
        sort_order=data.get("sort_order") or 0,
    )
    db.add(feature)
    await db.flush()
    await write_audit_log(
        db,
        action="maps.features.create",
        resource_type="map_feature",
        resource_id=feature.id,
        organization_id=layer.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added feature {feature.name} to {layer.code}",
        changes={"name": feature.name, "feature_type": feature.feature_type},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return feature


# -------- Evidence --------


async def get_evidence(db: AsyncSession, organization_id: UUID, evidence_id: UUID) -> EvidenceItem:
    item = await db.scalar(
        select(EvidenceItem).where(
            EvidenceItem.id == evidence_id, EvidenceItem.organization_id == organization_id
        )
    )
    if not item:
        raise NotFoundError("Evidence item not found")
    return item


async def list_evidence(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    evidence_type: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[EvidenceItem], int]:
    filters = [EvidenceItem.organization_id == organization_id]
    if status:
        filters.append(EvidenceItem.status == status)
    if evidence_type:
        filters.append(EvidenceItem.evidence_type == evidence_type)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(EvidenceItem.title.ilike(like), EvidenceItem.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(EvidenceItem).where(*filters)) or 0
    result = await db.execute(
        select(EvidenceItem)
        .where(*filters)
        .order_by(EvidenceItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_evidence(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> EvidenceItem:
    await _assert_links(db, organization_id, data)
    code = await _ensure_unique_code(
        db,
        model=EvidenceItem,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["title"], prefix="EVD-"),
    )
    item = EvidenceItem(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        indicator_id=data.get("indicator_id"),
        monitoring_result_id=data.get("monitoring_result_id"),
        evaluation_id=data.get("evaluation_id"),
        beneficiary_id=data.get("beneficiary_id"),
        report_id=data.get("report_id"),
        title=data["title"].strip(),
        code=code,
        evidence_type=data.get("evidence_type") or "document",
        status=data.get("status") or "draft",
        description=data.get("description"),
        collected_on=data.get("collected_on"),
        source=data.get("source"),
        file_url=data.get("file_url"),
        file_name=data.get("file_name"),
        mime_type=data.get("mime_type"),
        tags=data.get("tags") or [],
        created_by_id=actor_id,
    )
    db.add(item)
    await db.flush()
    await write_audit_log(
        db,
        action="evidence.create",
        resource_type="evidence_item",
        resource_id=item.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added evidence {item.code}",
        changes={"title": item.title, "code": item.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return item


async def update_evidence(
    db: AsyncSession,
    item: EvidenceItem,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> EvidenceItem:
    await _assert_links(db, item.organization_id, data)
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="EVD-")
        if new_code != item.code:
            data["code"] = await _ensure_unique_code(
                db, model=EvidenceItem, organization_id=item.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(item, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="evidence.update",
        resource_type="evidence_item",
        resource_id=item.id,
        organization_id=item.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated evidence {item.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return item


async def delete_evidence(
    db: AsyncSession,
    item: EvidenceItem,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="evidence.delete",
        resource_type="evidence_item",
        resource_id=item.id,
        organization_id=item.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted evidence {item.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(item)
    await db.flush()


# -------- Analytics + counts --------


async def phase6_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    reports = await db.scalar(
        select(func.count()).select_from(Report).where(Report.organization_id == organization_id)
    )
    published_reports = await db.scalar(
        select(func.count())
        .select_from(Report)
        .where(
            Report.organization_id == organization_id,
            Report.status.in_(["approved", "published"]),
        )
    )
    dashboards = await db.scalar(
        select(func.count())
        .select_from(SavedDashboard)
        .where(SavedDashboard.organization_id == organization_id)
    )
    map_layers = await db.scalar(
        select(func.count()).select_from(MapLayer).where(MapLayer.organization_id == organization_id)
    )
    map_features = await db.scalar(
        select(func.count())
        .select_from(MapFeature)
        .where(MapFeature.organization_id == organization_id)
    )
    evidence = await db.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.organization_id == organization_id)
    )
    verified_evidence = await db.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(
            EvidenceItem.organization_id == organization_id,
            EvidenceItem.status == "verified",
        )
    )
    return {
        "reports_count": reports or 0,
        "published_reports_count": published_reports or 0,
        "saved_dashboards_count": dashboards or 0,
        "map_layers_count": map_layers or 0,
        "map_features_count": map_features or 0,
        "evidence_count": evidence or 0,
        "verified_evidence_count": verified_evidence or 0,
    }


async def analytics_overview(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    p2 = await phase2_counts(db, organization_id)
    p3 = await phase3_counts(db, organization_id)
    p4 = await phase4_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    p6 = await phase6_counts(db, organization_id)

    report_by_status = await db.execute(
        select(Report.status, func.count())
        .where(Report.organization_id == organization_id)
        .group_by(Report.status)
    )
    evidence_by_type = await db.execute(
        select(EvidenceItem.evidence_type, func.count())
        .where(EvidenceItem.organization_id == organization_id)
        .group_by(EvidenceItem.evidence_type)
    )
    return {
        "delivery": p2,
        "finance": p3,
        "meal": p4,
        "field": p5,
        "insights": p6,
        "reports_by_status": {row[0]: row[1] for row in report_by_status.all()},
        "evidence_by_type": {row[0]: row[1] for row in evidence_by_type.all()},
    }
