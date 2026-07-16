"""AI Copilot tool registry.

Each tool wraps an existing service call and returns a uniform envelope::

    {"ok": bool, "data": Any, "citations": list[dict]}

where each citation is ``{"type": str, "id": str, "label": str, "href"?: str}``.

Tools are deliberately thin adapters over the existing domain services — they do
NOT re-implement any querying logic. The runner scopes every call by
``organization_id`` and skips tools the caller lacks permission for.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

# Domain services (thin wrappers only — no new query logic here)
from app.services import beneficiaries as beneficiaries_service
from app.services import finance as finance_service
from app.services import insights as insights_service
from app.services import meal as meal_service
from app.services import programs as programs_service
from app.services import surveys as surveys_service

ToolFn = Callable[..., Awaitable[dict[str, Any]]]

_DEFAULT_LIMIT = 8


def _search_arg(query: str) -> Optional[str]:
    """Only treat short, keyword-like queries as a list search filter.

    A full conversational sentence (e.g. "List our programs please") must not be
    used as an ILIKE filter — it would match nothing. In that case we ground the
    copilot on the org's most recent records instead.
    """
    q = (query or "").strip()
    if not q:
        return None
    words = q.split()
    if len(words) <= 2 and len(q) <= 40:
        return q
    return None


def _citation(type_: str, id_: Any, label: str, href: Optional[str] = None) -> dict[str, Any]:
    cite = {"type": type_, "id": str(id_), "label": label}
    if href:
        cite["href"] = href
    return cite


def _empty(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data if data is not None else {}, "citations": []}


# -------- Individual tools --------


async def _tool_org_snapshot(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    from app.services import ai as ai_service

    snapshot = await ai_service._org_snapshot(db, organization_id)
    return {"ok": True, "data": snapshot, "citations": []}


async def _tool_search_beneficiaries(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await beneficiaries_service.list_beneficiaries(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "beneficiaries": [
            {
                "id": str(b.id),
                "code": b.code,
                "name": f"{b.first_name} {b.last_name}".strip(),
                "sex": b.sex,
                "status": b.status,
            }
            for b in items
        ],
    }
    citations = [
        _citation("beneficiary", b.id, f"{b.first_name} {b.last_name}".strip() or b.code)
        for b in items
    ]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_projects(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await programs_service.list_projects(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "projects": [
            {"id": str(p.id), "code": p.code, "name": p.name, "status": p.status}
            for p in items
        ],
    }
    citations = [_citation("project", p.id, p.name) for p in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_programs(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await programs_service.list_programs(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "programs": [
            {"id": str(p.id), "code": p.code, "name": p.name, "status": p.status}
            for p in items
        ],
    }
    citations = [_citation("program", p.id, p.name) for p in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_grants(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await finance_service.list_grants(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "grants": [
            {
                "id": str(g.id),
                "code": g.code,
                "name": g.name,
                "status": g.status,
                "currency": g.currency,
                "amount_awarded": str(g.amount_awarded),
                "amount_received": str(g.amount_received),
                "end_date": str(g.end_date) if g.end_date else None,
            }
            for g in items
        ],
    }
    citations = [_citation("grant", g.id, g.name) for g in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_indicators(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await meal_service.list_indicators(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    progress = await meal_service.indicator_progress(db, organization_id, limit=_DEFAULT_LIMIT)
    data = {
        "total": total,
        "indicators": [
            {"id": str(i.id), "code": i.code, "name": i.name, "status": i.status}
            for i in items
        ],
        "progress": progress,
    }
    citations = [_citation("indicator", i.id, i.name) for i in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_surveys(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await surveys_service.list_surveys(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "surveys": [
            {"id": str(s.id), "code": s.code, "name": s.name, "status": s.status}
            for s in items
        ],
    }
    citations = [_citation("survey", s.id, s.name) for s in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_reports(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await insights_service.list_reports(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "reports": [
            {
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "report_type": r.report_type,
                "status": r.status,
            }
            for r in items
        ],
    }
    citations = [_citation("report", r.id, r.name) for r in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_activities_tasks(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    from datetime import date

    open_tasks: list = []
    total_open = 0
    for status in ("todo", "in_progress", "blocked"):
        items, total = await programs_service.list_tasks(
            db, organization_id, page=1, page_size=_DEFAULT_LIMIT, status=status
        )
        total_open += total
        open_tasks.extend(items)

    today = date.today()
    task_rows = []
    overdue_rows = []
    for t in open_tasks[: _DEFAULT_LIMIT * 2]:
        is_overdue = bool(t.due_date and t.due_date < today)
        row = {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "due_date": str(t.due_date) if t.due_date else None,
            "overdue": is_overdue,
        }
        task_rows.append(row)
        if is_overdue:
            overdue_rows.append(row)
    data = {
        "open_tasks_total": total_open,
        "overdue_count": len(overdue_rows),
        "tasks": task_rows,
    }
    citations = [_citation("task", t.id, t.title) for t in open_tasks[:_DEFAULT_LIMIT]]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_knowledge(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    from app.services import ai as ai_service

    docs = await ai_service.search_knowledge(db, organization_id, query=query, limit=5)
    data = {
        "documents": [
            {
                "id": str(d.id),
                "code": d.code,
                "name": d.name,
                "summary": (d.summary or d.content or "")[:400],
            }
            for d in docs
        ]
    }
    citations = [_citation("knowledge", d.id, d.name) for d in docs]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_search_evidence(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    items, total = await insights_service.list_evidence(
        db, organization_id, page=1, page_size=_DEFAULT_LIMIT, search=_search_arg(query)
    )
    data = {
        "total": total,
        "evidence": [
            {
                "id": str(e.id),
                "code": e.code,
                "title": e.title,
                "evidence_type": e.evidence_type,
                "status": e.status,
            }
            for e in items
        ],
    }
    citations = [_citation("evidence", e.id, e.title) for e in items]
    return {"ok": True, "data": data, "citations": citations}


async def _tool_indicator_progress(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    progress = await meal_service.indicator_progress(db, organization_id, limit=25)
    citations = [
        _citation("indicator", row["indicator_id"], row["name"])
        for row in progress
        if row.get("indicator_id")
    ]
    return {"ok": True, "data": {"progress": progress}, "citations": citations}


async def _tool_survey_analytics(
    db: AsyncSession,
    organization_id: UUID,
    query: str,
    *,
    survey_id: Optional[UUID] = None,
    **_: Any,
) -> dict[str, Any]:
    target_id = survey_id
    if target_id is None:
        surveys, _total = await surveys_service.list_surveys(
            db, organization_id, page=1, page_size=1, status="published"
        )
        if not surveys:
            return {"ok": False, "data": {"reason": "no published survey"}, "citations": []}
        target_id = surveys[0].id
    try:
        analytics = await surveys_service.response_analytics(db, organization_id, target_id)
    except Exception:  # noqa: BLE001
        return {"ok": False, "data": {"reason": "analytics unavailable"}, "citations": []}
    return {
        "ok": True,
        "data": analytics,
        "citations": [_citation("survey", target_id, "Survey analytics")],
    }


async def _tool_analytics_overview(
    db: AsyncSession, organization_id: UUID, query: str, **_: Any
) -> dict[str, Any]:
    overview = await insights_service.analytics_overview(db, organization_id)
    return {"ok": True, "data": overview, "citations": []}


# -------- Registry --------


TOOLS: dict[str, dict[str, Any]] = {
    "org_snapshot": {"fn": _tool_org_snapshot, "required_permissions": set()},
    "search_beneficiaries": {
        "fn": _tool_search_beneficiaries,
        "required_permissions": {"beneficiaries:read"},
    },
    "search_projects": {"fn": _tool_search_projects, "required_permissions": {"programs:read"}},
    "search_programs": {"fn": _tool_search_programs, "required_permissions": {"programs:read"}},
    "search_grants": {"fn": _tool_search_grants, "required_permissions": {"grants:read"}},
    "search_indicators": {
        "fn": _tool_search_indicators,
        "required_permissions": {"indicators:read"},
    },
    "search_surveys": {"fn": _tool_search_surveys, "required_permissions": {"surveys:read"}},
    "search_reports": {"fn": _tool_search_reports, "required_permissions": {"reports:read"}},
    "search_activities_tasks": {
        "fn": _tool_search_activities_tasks,
        "required_permissions": {"tasks:read"},
    },
    "search_knowledge": {
        "fn": _tool_search_knowledge,
        "required_permissions": {"knowledge:read"},
    },
    "search_evidence": {"fn": _tool_search_evidence, "required_permissions": {"evidence:read"}},
    "indicator_progress": {
        "fn": _tool_indicator_progress,
        "required_permissions": {"indicators:read"},
    },
    "survey_analytics": {"fn": _tool_survey_analytics, "required_permissions": {"surveys:read"}},
    "analytics_overview": {"fn": _tool_analytics_overview, "required_permissions": set()},
}


# -------- Selection + execution --------


def _tool_allowed(required: set[str], permissions: set[str]) -> bool:
    """A read tool runs if the caller can use AI at all, or holds a domain perm.

    Rule: ``ai:use`` grants access to every read tool; otherwise the caller must
    hold at least one of the tool's declared ``required_permissions``.
    """
    if not required:
        return True
    if "ai:use" in permissions:
        return True
    return bool(required & permissions)


def select_tools(query: str) -> list[str]:
    """Keyword heuristic selecting 1-5 relevant tools for a query."""
    q = (query or "").lower()
    selected: list[str] = []

    def add(name: str) -> None:
        if name not in selected and name in TOOLS:
            selected.append(name)

    if any(k in q for k in ("beneficiar", "household", "communit", "women", "gender", "girl")):
        add("search_beneficiaries")
    if any(k in q for k in ("grant", "donor", "funding", "award")):
        add("search_grants")
    if any(k in q for k in ("budget", "burn", "spend", "expense", "finance")):
        add("search_grants")
    if any(k in q for k in ("indicator", "behind", "target", "outcome", "result")):
        add("search_indicators")
        add("indicator_progress")
    if any(k in q for k in ("survey", "form", "response")):
        add("search_surveys")
    if any(k in q for k in ("project",)):
        add("search_projects")
    if any(k in q for k in ("program", "programme", "portfolio")):
        add("search_programs")
    if any(k in q for k in ("overdue", "task", "activit", "deadline", "todo")):
        add("search_activities_tasks")
    if any(k in q for k in ("report", "donor report", "narrative")):
        add("search_reports")
    if any(k in q for k in ("knowledge", "sop", "policy", "guideline", "procedure", "how do")):
        add("search_knowledge")
    if any(k in q for k in ("evidence", "verification", "proof", "document")):
        add("search_evidence")

    if not selected:
        # Default: give the model a portfolio picture + knowledge grounding.
        add("org_snapshot")
        add("search_knowledge")

    # Always anchor with the org snapshot so numbers are grounded.
    if "org_snapshot" not in selected:
        selected.insert(0, "org_snapshot")

    return selected[:5]


async def run_tools(
    db: AsyncSession,
    organization_id: UUID,
    tool_names: list[str],
    query: str,
    permissions: list[str] | set[str],
    *,
    tool_kwargs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Run the selected tools, scoped to the organization + caller permissions.

    Returns ``{results, citations, tools_used}`` where ``results`` maps tool
    name to its envelope.
    """
    permset = set(permissions or [])
    kwargs = tool_kwargs or {}
    results: dict[str, Any] = {}
    citations: list[dict[str, Any]] = []
    tools_used: list[str] = []

    for name in tool_names:
        spec = TOOLS.get(name)
        if not spec:
            continue
        if not _tool_allowed(spec["required_permissions"], permset):
            continue
        try:
            envelope = await spec["fn"](db, organization_id, query, **kwargs)
        except Exception as exc:  # noqa: BLE001
            results[name] = {"ok": False, "data": {"error": str(exc)[:200]}, "citations": []}
            continue
        results[name] = envelope
        tools_used.append(name)
        for cite in envelope.get("citations") or []:
            if cite not in citations:
                citations.append(cite)

    return {"results": results, "citations": citations, "tools_used": tools_used}
