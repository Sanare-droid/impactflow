"""Epic 5 — report templates, versions, multi-format exports (extends insights Report)."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any, Optional
from uuid import UUID
from xml.sax.saxutils import escape

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.report import Report
from app.models.report_template import ReportTemplate, ReportVersion
from app.services.audit import write_audit_log
from app.services.insights import get_report, render_report_markdown
from app.services.programs import make_code, _ensure_unique_code

# Built-in donor/executive templates — cloned into orgs on demand
SYSTEM_TEMPLATES: list[dict[str, Any]] = [
    {
        "code": "generic-ngo",
        "name": "Generic NGO Report",
        "category": "generic",
        "report_type": "progress",
        "narrative_style": "formal",
        "description": "Standard NGO progress report with summary, indicators, and budget.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "objectives", "title": "Objectives", "required": True},
            {"id": "progress", "title": "Progress", "required": True},
            {"id": "indicators", "title": "Indicators", "required": True},
            {"id": "beneficiaries", "title": "Beneficiary Statistics", "required": True},
            {"id": "budget", "title": "Budget Summary", "required": True},
            {"id": "challenges", "title": "Challenges", "required": False},
            {"id": "lessons", "title": "Lessons Learned", "required": False},
            {"id": "next", "title": "Next Steps", "required": True},
        ],
        "required_metrics": ["beneficiary_reach", "indicator_on_track", "budget_utilization_pct"],
        "export_preferences": {"default_format": "pdf", "include_charts": True},
    },
    {
        "code": "usaid-style",
        "name": "USAID Style",
        "category": "usaid",
        "report_type": "donor",
        "narrative_style": "results_framework",
        "description": "Results-framework oriented donor report.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "ir", "title": "Intermediate Results", "required": True},
            {"id": "outputs", "title": "Outputs", "required": True},
            {"id": "outcomes", "title": "Outcomes", "required": True},
            {"id": "indicators", "title": "Performance Indicators", "required": True},
            {"id": "gender", "title": "Gender & Inclusion", "required": True},
            {"id": "budget", "title": "Financial Summary", "required": True},
            {"id": "risks", "title": "Risks & Mitigation", "required": True},
            {"id": "appendices", "title": "Appendices", "required": False},
        ],
        "required_metrics": ["indicator_performance", "gender", "budget_utilization_pct"],
        "export_preferences": {"default_format": "docx"},
    },
    {
        "code": "eu-style",
        "name": "European Union Style",
        "category": "eu",
        "report_type": "donor",
        "narrative_style": "formal",
        "description": "EU-style interim / final narrative report.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "relevance", "title": "Relevance", "required": True},
            {"id": "effectiveness", "title": "Effectiveness", "required": True},
            {"id": "efficiency", "title": "Efficiency", "required": True},
            {"id": "impact", "title": "Impact", "required": True},
            {"id": "sustainability", "title": "Sustainability", "required": True},
            {"id": "budget", "title": "Budget Consumption", "required": True},
        ],
        "required_metrics": ["program_efficiency_pct", "cost_per_beneficiary"],
        "export_preferences": {"default_format": "pdf"},
    },
    {
        "code": "world-bank-style",
        "name": "World Bank Style",
        "category": "world_bank",
        "report_type": "donor",
        "narrative_style": "formal",
        "description": "Results and implementation status for development partners.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "pdo", "title": "Project Development Objectives", "required": True},
            {"id": "implementation", "title": "Implementation Status", "required": True},
            {"id": "indicators", "title": "Results Framework", "required": True},
            {"id": "fiduciary", "title": "Fiduciary Overview", "required": True},
            {"id": "risks", "title": "Risk Ratings", "required": True},
        ],
        "required_metrics": ["indicator_performance", "budget_utilization_pct", "risk_heat"],
        "export_preferences": {"default_format": "pdf"},
    },
    {
        "code": "un-agency",
        "name": "UN Agency Style",
        "category": "un",
        "report_type": "annual",
        "narrative_style": "human_rights",
        "description": "UN-style annual results report.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "context", "title": "Context", "required": True},
            {"id": "results", "title": "Key Results", "required": True},
            {"id": "beneficiaries", "title": "People Reached", "required": True},
            {"id": "partnerships", "title": "Partnerships", "required": False},
            {"id": "lessons", "title": "Lessons Learned", "required": True},
        ],
        "required_metrics": ["beneficiary_reach", "communities_reached"],
        "export_preferences": {"default_format": "pdf"},
    },
    {
        "code": "foundation-report",
        "name": "Foundation Report",
        "category": "foundation",
        "report_type": "donor",
        "narrative_style": "storytelling",
        "description": "Foundation-friendly impact narrative with stories.",
        "sections": [
            {"id": "exec", "title": "Highlights", "required": True},
            {"id": "story", "title": "Success Story", "required": True},
            {"id": "impact", "title": "Impact Metrics", "required": True},
            {"id": "budget", "title": "Use of Funds", "required": True},
            {"id": "thanks", "title": "Acknowledgement", "required": False},
        ],
        "required_metrics": ["beneficiary_reach", "indicator_on_track"],
        "export_preferences": {"default_format": "pptx"},
    },
    {
        "code": "government-report",
        "name": "Government Report",
        "category": "government",
        "report_type": "compliance",
        "narrative_style": "formal",
        "description": "Government compliance and accountability report.",
        "sections": [
            {"id": "exec", "title": "Executive Summary", "required": True},
            {"id": "compliance", "title": "Compliance Status", "required": True},
            {"id": "indicators", "title": "KPI Performance", "required": True},
            {"id": "budget", "title": "Budget Execution", "required": True},
            {"id": "risks", "title": "Risks", "required": True},
        ],
        "required_metrics": ["budget_utilization_pct", "compliance"],
        "export_preferences": {"default_format": "docx"},
    },
    {
        "code": "csr-report",
        "name": "Corporate CSR Report",
        "category": "csr",
        "report_type": "impact",
        "narrative_style": "executive",
        "description": "Corporate social responsibility impact brief.",
        "sections": [
            {"id": "exec", "title": "Impact Snapshot", "required": True},
            {"id": "sdg", "title": "SDG Alignment", "required": False},
            {"id": "reach", "title": "Community Reach", "required": True},
            {"id": "stories", "title": "Case Studies", "required": True},
        ],
        "required_metrics": ["communities_reached", "beneficiary_reach"],
        "export_preferences": {"default_format": "pptx"},
    },
    {
        "code": "executive-brief",
        "name": "Executive Brief",
        "category": "generic",
        "report_type": "executive_brief",
        "narrative_style": "concise",
        "description": "One-page board / donor meeting brief.",
        "sections": [
            {"id": "highlights", "title": "Highlights", "required": True},
            {"id": "kpis", "title": "KPIs", "required": True},
            {"id": "risks", "title": "Risks", "required": True},
            {"id": "decisions", "title": "Recommended Decisions", "required": True},
            {"id": "finance", "title": "Financial Snapshot", "required": True},
        ],
        "required_metrics": ["portfolio_health", "budget_utilization_pct", "risk_heat"],
        "export_preferences": {"default_format": "pdf"},
    },
]


def list_system_templates() -> list[dict[str, Any]]:
    return [{**t, "is_system": True, "organization_id": None} for t in SYSTEM_TEMPLATES]


async def get_template(
    db: AsyncSession, organization_id: UUID, template_id: UUID
) -> ReportTemplate:
    row = await db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            or_(
                ReportTemplate.organization_id == organization_id,
                ReportTemplate.is_system.is_(True),
            ),
        )
    )
    if not row:
        raise NotFoundError("Report template not found")
    return row


async def list_templates(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
    category: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    system = list_system_templates()
    if category:
        system = [t for t in system if t["category"] == category]

    filters = [ReportTemplate.organization_id == organization_id]
    if category:
        filters.append(ReportTemplate.category == category)
    org_rows = list(
        (
            await db.scalars(
                select(ReportTemplate).where(*filters).order_by(ReportTemplate.name.asc())
            )
        ).all()
    )
    org_items = [
        {
            "id": str(r.id),
            "organization_id": str(r.organization_id) if r.organization_id else None,
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "category": r.category,
            "report_type": r.report_type,
            "narrative_style": r.narrative_style,
            "sections": r.sections,
            "required_metrics": r.required_metrics,
            "branding": r.branding,
            "export_preferences": r.export_preferences,
            "is_system": r.is_system,
            "status": r.status,
            "cloned_from_id": str(r.cloned_from_id) if r.cloned_from_id else None,
        }
        for r in org_rows
    ]
    combined = system + org_items
    total = len(combined)
    start = (page - 1) * page_size
    return combined[start : start + page_size], total


async def clone_template(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    code: Optional[str] = None,
    template_id: Optional[UUID] = None,
    name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ReportTemplate:
    source: Optional[dict[str, Any]] = None
    cloned_from: Optional[UUID] = None
    if template_id:
        row = await get_template(db, organization_id, template_id)
        source = {
            "name": row.name,
            "code": row.code,
            "description": row.description,
            "category": row.category,
            "report_type": row.report_type,
            "narrative_style": row.narrative_style,
            "sections": row.sections,
            "required_metrics": row.required_metrics,
            "branding": row.branding,
            "export_preferences": row.export_preferences,
        }
        cloned_from = row.id
    elif code:
        match = next((t for t in SYSTEM_TEMPLATES if t["code"] == code), None)
        if not match:
            raise NotFoundError("System template not found")
        source = match
    else:
        raise NotFoundError("Provide template code or id")

    unique_code = await _ensure_unique_code(
        db,
        model=ReportTemplate,
        organization_id=organization_id,
        code=make_code(source["code"], prefix="TPL-"),
    )
    tpl = ReportTemplate(
        organization_id=organization_id,
        name=(name or source["name"]).strip(),
        code=unique_code,
        description=source.get("description"),
        category=source.get("category") or "generic",
        report_type=source.get("report_type") or "donor",
        narrative_style=source.get("narrative_style") or "formal",
        sections=list(source.get("sections") or []),
        required_metrics=list(source.get("required_metrics") or []),
        branding=dict(source.get("branding") or {}),
        export_preferences=dict(source.get("export_preferences") or {}),
        is_system=False,
        status="active",
        cloned_from_id=cloned_from,
        created_by_id=actor_id,
    )
    db.add(tpl)
    await db.flush()
    await write_audit_log(
        db,
        action="report_templates.clone",
        resource_type="report_template",
        resource_id=tpl.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Cloned report template {tpl.code}",
        changes={"source": code or str(template_id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return tpl


async def create_report_version(
    db: AsyncSession,
    *,
    report: Report,
    actor_id: UUID,
    actor_email: str,
    changelog: Optional[str] = None,
    citations: Optional[list] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ReportVersion:
    max_v = await db.scalar(
        select(func.max(ReportVersion.version)).where(ReportVersion.report_id == report.id)
    )
    version = (max_v or 0) + 1
    row = ReportVersion(
        organization_id=report.organization_id,
        report_id=report.id,
        version=version,
        title=report.name,
        summary=report.summary,
        content=report.content,
        sections=list(report.sections or []),
        changelog=changelog or f"Version {version}",
        status=report.status,
        created_by_id=actor_id,
        citations=citations or [],
    )
    db.add(row)
    await db.flush()
    meta = dict(report.metadata_ or {})
    meta["current_version"] = version
    report.metadata_ = meta
    await db.flush()
    await write_audit_log(
        db,
        action="reports.version",
        resource_type="report",
        resource_id=report.id,
        organization_id=report.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created report version {version} for {report.code}",
        changes={"version": version},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def list_report_versions(
    db: AsyncSession, organization_id: UUID, report_id: UUID
) -> list[ReportVersion]:
    await get_report(db, organization_id, report_id)
    rows = await db.scalars(
        select(ReportVersion)
        .where(
            ReportVersion.organization_id == organization_id,
            ReportVersion.report_id == report_id,
        )
        .order_by(ReportVersion.version.desc())
    )
    return list(rows.all())


def _html_document(title: str, body_md: str) -> str:
    # Simple markdown-ish → HTML (paragraphs + headings)
    parts: list[str] = []
    for line in body_md.splitlines():
        if line.startswith("# "):
            parts.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            parts.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("### "):
            parts.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("- "):
            parts.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip() == "":
            parts.append("<br/>")
        else:
            parts.append(f"<p>{escape(line)}</p>")
    body = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<title>{escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;max-width:800px;margin:2rem auto;"
        "line-height:1.55;color:#1c1917}h1,h2{color:#134e4a}li{margin-left:1.2rem}"
        "@media print{body{margin:1rem}}</style></head><body>"
        f"{body}<hr/><p><em>ImpactFlow · grounded export</em></p>"
        "</body></html>"
    )


def _csv_bytes(report: Report) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["field", "value"])
    w.writerow(["name", report.name])
    w.writerow(["code", report.code])
    w.writerow(["type", report.report_type])
    w.writerow(["status", report.status])
    w.writerow(["period_start", report.period_start or ""])
    w.writerow(["period_end", report.period_end or ""])
    w.writerow(["summary", report.summary or ""])
    w.writerow(["content", report.content or ""])
    return buf.getvalue().encode("utf-8")


def _xlsx_xml(report: Report) -> bytes:
    """SpreadsheetML (Excel-compatible XML) — same approach as survey exports."""
    rows = [
        ("Name", report.name),
        ("Code", report.code),
        ("Type", report.report_type),
        ("Status", report.status),
        ("Period Start", str(report.period_start or "")),
        ("Period End", str(report.period_end or "")),
        ("Summary", report.summary or ""),
        ("Content", (report.content or "")[:32000]),
    ]
    cells = []
    for i, (k, v) in enumerate(rows, start=1):
        cells.append(
            f'<Row><Cell><Data ss:Type="String">{escape(k)}</Data></Cell>'
            f'<Cell><Data ss:Type="String">{escape(str(v))}</Data></Cell></Row>'
        )
    xml = (
        '<?xml version="1.0"?>\n'
        '<?mso-application progid="Excel.Sheet"?>\n'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        "<Worksheet ss:Name=\"Report\">"
        "<Table>"
        + "".join(cells)
        + "</Table></Worksheet></Workbook>"
    )
    return xml.encode("utf-8")


def _docx_bytes(title: str, markdown: str) -> bytes:
    """Minimal OOXML .docx (Word) package."""
    paragraphs = []
    for line in markdown.splitlines():
        text = escape(line) if line else " "
        paragraphs.append(
            f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paragraphs)}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def _pptx_bytes(title: str, markdown: str) -> bytes:
    """Minimal OOXML .pptx with one title slide and content slides."""
    slides_text = []
    chunk: list[str] = []
    for line in markdown.splitlines():
        chunk.append(line)
        if len(chunk) >= 12:
            slides_text.append("\n".join(chunk))
            chunk = []
    if chunk:
        slides_text.append("\n".join(chunk))
    if not slides_text:
        slides_text = [title]

    def slide_xml(text: str, idx: int) -> str:
        lines = [escape(l) for l in text.splitlines()[:15]]
        body = "&#xA;".join(lines)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            "<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/>"
            "<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>"
            f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            "<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>"
            f'<a:p><a:r><a:t>{escape(title) if idx == 0 else f"Slide {idx + 1}"}</a:t></a:r></a:p>'
            f'<a:p><a:r><a:t>{body}</a:t></a:r></a:p>'
            "</p:txBody></p:sp></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )

    content_types_parts = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/ppt/presentation.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
    ]
    for i in range(len(slides_text)):
        content_types_parts.append(
            f'<Override PartName="/ppt/slides/slide{i + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        + "".join(content_types_parts)
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )
    sld_ids = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(len(slides_text))
    )
    presentation = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f"<p:sldIdLst>{sld_ids}</p:sldIdLst></p:presentation>"
    )
    pres_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i + 1}.xml"/>'
            for i in range(len(slides_text))
        )
        + "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", presentation)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        for i, text in enumerate(slides_text):
            zf.writestr(f"ppt/slides/slide{i + 1}.xml", slide_xml(text, i))
    return buf.getvalue()


def export_report_payload(report: Report, fmt: str) -> tuple[bytes, str, str]:
    """Return (bytes, media_type, filename_ext) for supported formats."""
    md = render_report_markdown(report)
    fmt = (fmt or "markdown").lower()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in report.code) or "report"

    if fmt == "markdown":
        return md.encode("utf-8"), "text/markdown; charset=utf-8", "md"
    if fmt == "html":
        return _html_document(report.name, md).encode("utf-8"), "text/html; charset=utf-8", "html"
    if fmt == "pdf":
        # Print-ready HTML intended for browser/PDF printers (no binary PDF engine dependency)
        html = _html_document(report.name, md)
        return html.encode("utf-8"), "text/html; charset=utf-8", "pdf.html"
    if fmt == "csv":
        return _csv_bytes(report), "text/csv; charset=utf-8", "csv"
    if fmt in ("xlsx", "excel"):
        return _xlsx_xml(report), "application/vnd.ms-excel", "xls"
    if fmt == "docx":
        return (
            _docx_bytes(report.name, md),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        )
    if fmt == "pptx":
        return (
            _pptx_bytes(report.name, md),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "pptx",
        )
    raise NotFoundError(f"Unsupported export format: {fmt}")
