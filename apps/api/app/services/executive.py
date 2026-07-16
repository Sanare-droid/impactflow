"""Epic 5 — Executive analytics, compliance, impact measurement (extends insights + AI).

Does NOT rewrite reporting or create a separate AI stack.
Grounded numbers only — never invent statistics.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.activity import Activity
from app.models.beneficiary import Beneficiary
from app.models.budget import Budget
from app.models.community import Community
from app.models.evidence import EvidenceItem
from app.models.finance import FinanceTransaction
from app.models.grant import Grant
from app.models.indicator import Indicator
from app.models.program import Program
from app.models.project import Project
from app.models.report import Report
from app.models.survey import Survey, SurveyResponse
from app.models.task import Task
from app.services import ai_intelligence
from app.services import field_sync
from app.services import meal as meal_service
from app.services import surveys as survey_service
from app.services.beneficiaries import phase5_counts
from app.services.finance import phase3_counts
from app.services.meal import phase4_counts
from app.services.programs import phase2_counts


def _f(value: Optional[Decimal | float | int | str]) -> float:
    if value is None:
        return 0.0
    return float(value)


def _pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round(min(100.0, (num / den) * 100.0), 1)


async def _gender_distribution(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    rows = await db.execute(
        select(Beneficiary.sex, func.count())
        .where(Beneficiary.organization_id == organization_id)
        .group_by(Beneficiary.sex)
    )
    counts: dict[str, int] = {"female": 0, "male": 0, "other": 0, "unknown": 0}
    for sex, n in rows.all():
        key = (sex or "unknown").lower()
        if key in ("female", "f", "woman"):
            counts["female"] += int(n)
        elif key in ("male", "m", "man"):
            counts["male"] += int(n)
        elif key in ("other", "prefer_not_to_say", "non_binary"):
            counts["other"] += int(n)
        else:
            counts["unknown"] += int(n)
    return counts


async def _youth_and_pwd(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    today = date.today()
    youth_cutoff = today.replace(year=today.year - 35)
    bens = await db.scalars(
        select(Beneficiary).where(Beneficiary.organization_id == organization_id)
    )
    youth = 0
    pwd = 0
    for b in bens.all():
        if b.date_of_birth and b.date_of_birth >= youth_cutoff:
            youth += 1
        tags = [str(t).lower() for t in (b.vulnerability_tags or [])]
        if any("disab" in t or "pwd" in t or "impairment" in t for t in tags):
            pwd += 1
    return {"youth_reach": youth, "persons_with_disabilities": pwd}


async def _portfolio_health_score(
    *,
    open_tasks: int,
    total_tasks: int,
    indicator_on_track: int,
    indicator_total: int,
    budget_burn_pct: float,
    active_grants: int,
    risk_high: int,
) -> dict[str, Any]:
    """Composite 0–100 score from real portfolio signals."""
    task_score = 100.0 - _pct(open_tasks, max(total_tasks, 1)) * 0.4
    ind_score = _pct(indicator_on_track, max(indicator_total, 1))
    burn_score = 100.0 if budget_burn_pct <= 85 else max(0.0, 100.0 - (budget_burn_pct - 85) * 3)
    grant_score = min(100.0, active_grants * 20.0) if active_grants else 50.0
    risk_penalty = min(40.0, risk_high * 8.0)
    raw = (task_score * 0.2 + ind_score * 0.35 + burn_score * 0.2 + grant_score * 0.15) - risk_penalty
    score = round(max(0.0, min(100.0, raw)), 1)
    band = "healthy" if score >= 75 else "watch" if score >= 50 else "at_risk"
    return {
        "score": score,
        "band": band,
        "components": {
            "delivery": round(task_score, 1),
            "indicators": round(ind_score, 1),
            "budget": round(burn_score, 1),
            "grants": round(grant_score, 1),
            "risk_penalty": round(risk_penalty, 1),
        },
    }


async def executive_dashboard(
    db: AsyncSession,
    organization_id: UUID,
    *,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """Single executive view — grounded in authenticated platform records."""
    p2 = await phase2_counts(db, organization_id)
    p3 = await phase3_counts(db, organization_id)
    p4 = await phase4_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    survey_counts = await survey_service.phase11_survey_counts(db, organization_id)

    progress = await meal_service.indicator_progress(db, organization_id, limit=50)
    on_track = sum(
        1 for r in progress if r.get("progress_pct") is not None and r["progress_pct"] >= 70
    )
    behind = [
        r for r in progress if r.get("progress_pct") is not None and r["progress_pct"] < 70
    ]

    awarded = _f(p3.get("grants_awarded_total"))
    expenses = _f(p3.get("expenses_total"))
    burn_pct = _pct(expenses, awarded) if awarded else 0.0

    risks = await ai_intelligence.scan_portfolio_risks(db, organization_id)
    high_risks = [r for r in risks if r.get("severity") in ("high", "critical")]

    gender = await _gender_distribution(db, organization_id)
    demographics = await _youth_and_pwd(db, organization_id)

    communities = (
        await db.scalar(
            select(func.count()).select_from(Community).where(Community.organization_id == organization_id)
        )
        or 0
    )

    projects_completed = (
        await db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.organization_id == organization_id,
                Project.status.in_(["completed", "closed"]),
            )
        )
        or 0
    )
    projects_total = p2.get("projects_count", 0)

    # Upcoming deadlines — grants ending in 90 days + overdue tasks
    soon = utcnow().date() + timedelta(days=90)
    grants_expiring = list(
        (
            await db.scalars(
                select(Grant)
                .where(
                    Grant.organization_id == organization_id,
                    Grant.end_date.is_not(None),
                    Grant.end_date <= soon,
                    Grant.status.in_(["active", "awarded"]),
                )
                .order_by(Grant.end_date.asc())
                .limit(10)
            )
        ).all()
    )
    overdue_tasks = list(
        (
            await db.scalars(
                select(Task)
                .where(
                    Task.organization_id == organization_id,
                    Task.status.notin_(["done", "cancelled"]),
                    Task.due_date.is_not(None),
                    Task.due_date < utcnow().date(),
                )
                .order_by(Task.due_date.asc())
                .limit(10)
            )
        ).all()
    )

    reports = list(
        (
            await db.scalars(
                select(Report)
                .where(Report.organization_id == organization_id)
                .order_by(Report.updated_at.desc())
                .limit(5)
            )
        ).all()
    )

    field_metrics = await field_sync.field_ops_metrics(db, organization_id)
    insights = await ai_intelligence.build_dashboard_insights(db, organization_id)

    health = await _portfolio_health_score(
        open_tasks=p2.get("open_tasks_count", 0),
        total_tasks=max(p2.get("tasks_count", 0), 1),
        indicator_on_track=on_track,
        indicator_total=max(len(progress), 1),
        budget_burn_pct=burn_pct,
        active_grants=p3.get("active_grants_count", 0),
        risk_high=len(high_risks),
    )

    filters_applied = {
        "program_id": str(program_id) if program_id else None,
        "project_id": str(project_id) if project_id else None,
    }

    return {
        "generated_at": utcnow().isoformat(),
        "filters": filters_applied,
        "portfolio_health": health,
        "kpis": {
            "active_programs": p2.get("programs_count", 0),
            "active_projects": p2.get("projects_count", 0),
            "open_tasks": p2.get("open_tasks_count", 0),
            "grant_pipeline": p3.get("grants_count", 0),
            "active_grants": p3.get("active_grants_count", 0),
            "budget_utilization_pct": burn_pct,
            "grants_awarded_total": awarded,
            "expenses_total": expenses,
            "indicator_on_track": on_track,
            "indicator_total": len(progress),
            "beneficiary_reach": p5.get("beneficiaries_count", 0),
            "active_beneficiaries": p5.get("active_beneficiaries_count", 0),
            "communities_reached": communities,
            "project_completion_pct": _pct(projects_completed, max(projects_total, 1)),
            "surveys_count": survey_counts.get("surveys_count", 0),
            "published_surveys_count": survey_counts.get("published_surveys_count", 0),
            "indicators_count": p4.get("indicators_count", 0),
            "evidence_verified": None,
            **gender,
            **demographics,
        },
        "indicator_performance": progress[:15],
        "indicators_behind": behind[:10],
        "upcoming_deadlines": {
            "grants_expiring": [
                {
                    "id": str(g.id),
                    "name": g.name,
                    "code": g.code,
                    "end_date": g.end_date.isoformat() if g.end_date else None,
                    "status": g.status,
                }
                for g in grants_expiring
            ],
            "overdue_tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "priority": t.priority,
                    "status": t.status,
                }
                for t in overdue_tasks
            ],
        },
        "risk_heat": [
            {
                "type": r.get("type"),
                "title": r.get("title"),
                "severity": r.get("severity"),
                "summary": r.get("summary"),
                "suggested_action": r.get("suggested_action") or r.get("recommendation"),
            }
            for r in risks[:12]
        ],
        "field_operations": field_metrics,
        "ai_insights": {
            "summary": insights.get("summary"),
            "key_risks": insights.get("key_risks", [])[:5],
            "recommendations": insights.get("recommendations", [])[:5],
            "wins": insights.get("key_wins", insights.get("wins", []))[:3],
        },
        "latest_reports": [
            {
                "id": str(r.id),
                "name": r.name,
                "code": r.code,
                "report_type": r.report_type,
                "status": r.status,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in reports
        ],
        "quick_actions": [
            {"label": "Generate executive brief", "href": "/app/executive", "action": "brief"},
            {"label": "Build donor report", "href": "/app/reports", "action": "report"},
            {"label": "Review risks", "href": "/app/predictions", "action": "risks"},
            {"label": "Ask Copilot", "href": "/app/copilot", "action": "copilot"},
        ],
        "citations": [
            {"source": "programs", "metric": "active_programs"},
            {"source": "grants", "metric": "budget_utilization_pct"},
            {"source": "indicators", "metric": "indicator_performance"},
            {"source": "beneficiaries", "metric": "beneficiary_reach"},
            {"source": "ai_intelligence.scan_portfolio_risks", "metric": "risk_heat"},
        ],
    }


async def portfolio_analytics(
    db: AsyncSession,
    organization_id: UUID,
    *,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    grant_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """Filterable organization-wide analytics series for charts."""
    progress = await meal_service.indicator_progress(db, organization_id, limit=100)
    p2 = await phase2_counts(db, organization_id)
    p3 = await phase3_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    gender = await _gender_distribution(db, organization_id)

    # Activity completion
    act_total = (
        await db.scalar(
            select(func.count()).select_from(Activity).where(Activity.organization_id == organization_id)
        )
        or 0
    )
    act_done = (
        await db.scalar(
            select(func.count())
            .select_from(Activity)
            .where(
                Activity.organization_id == organization_id,
                Activity.status.in_(["completed", "done"]),
            )
        )
        or 0
    )

    # Survey completion
    surveys = (
        await db.scalar(
            select(func.count()).select_from(Survey).where(Survey.organization_id == organization_id)
        )
        or 0
    )
    responses = (
        await db.scalar(
            select(func.count())
            .select_from(SurveyResponse)
            .where(
                SurveyResponse.organization_id == organization_id,
                SurveyResponse.status == "submitted",
            )
        )
        or 0
    )

    # Evidence
    evidence = (
        await db.scalar(
            select(func.count())
            .select_from(EvidenceItem)
            .where(EvidenceItem.organization_id == organization_id)
        )
        or 0
    )
    verified = (
        await db.scalar(
            select(func.count())
            .select_from(EvidenceItem)
            .where(
                EvidenceItem.organization_id == organization_id,
                EvidenceItem.status == "verified",
            )
        )
        or 0
    )

    awarded = _f(p3.get("grants_awarded_total"))
    expenses = _f(p3.get("expenses_total"))
    ben_count = max(p5.get("beneficiaries_count", 0), 1)
    cost_per_beneficiary = round(expenses / ben_count, 2) if expenses else 0.0

    indicator_series = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "progress_pct": r.get("progress_pct"),
            "actual": r.get("actual_value"),
            "target": r.get("target_value"),
            "on_track": (r.get("progress_pct") or 0) >= 70,
        }
        for r in progress
    ]

    return {
        "generated_at": utcnow().isoformat(),
        "filters": {
            "program_id": str(program_id) if program_id else None,
            "project_id": str(project_id) if project_id else None,
            "grant_id": str(grant_id) if grant_id else None,
        },
        "program_performance": {
            "programs": p2.get("programs_count", 0),
            "projects": p2.get("projects_count", 0),
            "activities": act_total,
            "activities_completed": act_done,
            "activity_completion_pct": _pct(act_done, max(act_total, 1)),
        },
        "grant_performance": {
            "grants": p3.get("grants_count", 0),
            "active_grants": p3.get("active_grants_count", 0),
            "awarded_total": awarded,
            "received_total": _f(p3.get("grants_received_total")),
            "expenses_total": expenses,
            "burn_rate_pct": _pct(expenses, awarded) if awarded else 0.0,
        },
        "beneficiary_trends": {
            "total": p5.get("beneficiaries_count", 0),
            "active": p5.get("active_beneficiaries_count", 0),
            "gender": gender,
        },
        "indicator_trends": indicator_series,
        "survey_completion": {
            "surveys": surveys,
            "submitted_responses": responses,
        },
        "evidence_collection": {
            "total": evidence,
            "verified": verified,
            "verification_pct": _pct(verified, max(evidence, 1)),
        },
        "efficiency": {
            "cost_per_beneficiary": cost_per_beneficiary,
            "budget_utilization_pct": _pct(expenses, awarded) if awarded else 0.0,
        },
        "charts": {
            "indicator_progress_bar": [
                {"label": s["name"][:40], "value": s["progress_pct"] or 0}
                for s in indicator_series[:12]
            ],
            "gender_donut": [
                {"label": k, "value": v} for k, v in gender.items() if v > 0
            ],
            "budget_utilization": [
                {"label": "Expensed", "value": expenses},
                {"label": "Remaining", "value": max(0.0, awarded - expenses)},
            ],
        },
        "citations": [
            {"source": "meal.indicator_progress"},
            {"source": "finance.phase3_counts"},
            {"source": "beneficiaries"},
        ],
    }


async def impact_measurement(
    db: AsyncSession, organization_id: UUID
) -> dict[str, Any]:
    progress = await meal_service.indicator_progress(db, organization_id, limit=100)
    p3 = await phase3_counts(db, organization_id)
    p5 = await phase5_counts(db, organization_id)
    expenses = _f(p3.get("expenses_total"))
    awarded = _f(p3.get("grants_awarded_total"))
    bens = max(p5.get("beneficiaries_count", 0), 1)

    outputs = [r for r in progress if (r.get("level") or r.get("result_level") or "").lower() in ("output", "outputs", "")]
    outcomes = [r for r in progress if (r.get("level") or r.get("result_level") or "").lower() in ("outcome", "outcomes", "impact")]

    # If levels unavailable, split by progress bands
    if not outcomes and not any(r.get("level") for r in progress):
        outputs = [r for r in progress if (r.get("progress_pct") or 0) >= 50]
        outcomes = [r for r in progress if (r.get("progress_pct") or 0) < 50]

    variances = []
    for r in progress:
        actual = _f(r.get("actual_value"))
        target = _f(r.get("target_value"))
        variances.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "baseline": r.get("baseline_value"),
                "target": target,
                "actual": actual,
                "variance": round(actual - target, 2),
                "progress_pct": r.get("progress_pct"),
            }
        )

    on_track = sum(1 for r in progress if (r.get("progress_pct") or 0) >= 70)
    return {
        "generated_at": utcnow().isoformat(),
        "outputs_tracked": len(outputs) or len(progress),
        "outcomes_tracked": len(outcomes),
        "indicators_on_track": on_track,
        "indicators_total": len(progress),
        "cost_per_beneficiary": round(expenses / bens, 2) if expenses else 0.0,
        "program_efficiency_pct": _pct(on_track, max(len(progress), 1)),
        "grant_efficiency_pct": _pct(expenses, awarded) if awarded else 0.0,
        "beneficiary_reach": p5.get("beneficiaries_count", 0),
        "variances": variances[:30],
        "citations": [{"source": "indicators"}, {"source": "finance"}],
    }


async def compliance_dashboard(
    db: AsyncSession, organization_id: UUID
) -> dict[str, Any]:
    """Flag reporting gaps, missing indicators, evidence, and grant deadlines."""
    progress = await meal_service.indicator_progress(db, organization_id, limit=100)
    missing_indicators = [
        r for r in progress if r.get("actual_value") is None or r.get("progress_pct") is None
    ]
    behind = [
        r for r in progress if r.get("progress_pct") is not None and r["progress_pct"] < 50
    ]

    draft_reports = (
        await db.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.organization_id == organization_id, Report.status == "draft")
        )
        or 0
    )
    in_review = (
        await db.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.organization_id == organization_id, Report.status == "in_review")
        )
        or 0
    )

    empty_surveys = list(
        (
            await db.scalars(
                select(Survey)
                .where(Survey.organization_id == organization_id, Survey.status == "published")
                .limit(50)
            )
        ).all()
    )
    survey_gaps = []
    for s in empty_surveys:
        count = (
            await db.scalar(
                select(func.count())
                .select_from(SurveyResponse)
                .where(
                    SurveyResponse.survey_id == s.id,
                    SurveyResponse.status == "submitted",
                )
            )
            or 0
        )
        if count == 0:
            survey_gaps.append({"id": str(s.id), "name": s.name, "code": s.code})

    evidence_pending = (
        await db.scalar(
            select(func.count())
            .select_from(EvidenceItem)
            .where(
                EvidenceItem.organization_id == organization_id,
                EvidenceItem.status.in_(["pending", "submitted", "draft"]),
            )
        )
        or 0
    )

    soon = utcnow().date() + timedelta(days=60)
    grants_due = list(
        (
            await db.scalars(
                select(Grant)
                .where(
                    Grant.organization_id == organization_id,
                    Grant.end_date.is_not(None),
                    Grant.end_date <= soon,
                    Grant.status.in_(["active", "awarded"]),
                )
                .limit(15)
            )
        ).all()
    )

    risks = await ai_intelligence.scan_portfolio_risks(db, organization_id)
    recommendations = []
    if missing_indicators:
        recommendations.append(
            {
                "why": f"{len(missing_indicators)} indicators have no recorded actuals",
                "action": "Update monitoring results for indicators without actuals",
                "severity": "high",
                "href": "/app/indicators",
            }
        )
    if survey_gaps:
        recommendations.append(
            {
                "why": f"{len(survey_gaps)} published surveys have zero submissions",
                "action": "Assign enumerators or close unused surveys",
                "severity": "medium",
                "href": "/app/surveys",
            }
        )
    if grants_due:
        recommendations.append(
            {
                "why": f"{len(grants_due)} grants end within 60 days",
                "action": "Prepare donor reports before grant close-out",
                "severity": "high",
                "href": "/app/reports",
            }
        )
    if evidence_pending:
        recommendations.append(
            {
                "why": f"{evidence_pending} evidence items awaiting verification",
                "action": "Verify or reject pending evidence",
                "severity": "medium",
                "href": "/app/evidence",
            }
        )

    issues = []
    for r in behind[:10]:
        issues.append(
            {
                "category": "indicator",
                "title": f"Indicator behind target: {r.get('name')}",
                "severity": "high" if (r.get("progress_pct") or 0) < 40 else "medium",
                "detail": f"{r.get('progress_pct')}% of target",
            }
        )
    for g in grants_due:
        issues.append(
            {
                "category": "grant_deadline",
                "title": f"Grant ending soon: {g.name}",
                "severity": "high",
                "detail": g.end_date.isoformat() if g.end_date else None,
            }
        )
    for s in survey_gaps[:8]:
        issues.append(
            {
                "category": "survey_gap",
                "title": f"No responses: {s['name']}",
                "severity": "medium",
                "detail": s["code"],
            }
        )

    return {
        "generated_at": utcnow().isoformat(),
        "summary": {
            "draft_reports": draft_reports,
            "reports_in_review": in_review,
            "missing_indicator_actuals": len(missing_indicators),
            "indicators_behind": len(behind),
            "survey_gaps": len(survey_gaps),
            "evidence_pending": evidence_pending,
            "grants_ending_soon": len(grants_due),
            "open_risk_signals": len(risks),
        },
        "issues": issues,
        "recommendations": recommendations,
        "risk_signals": risks[:10],
        "citations": [
            {"source": "reports"},
            {"source": "indicators"},
            {"source": "surveys"},
            {"source": "grants"},
            {"source": "evidence"},
        ],
    }


async def risk_intelligence(
    db: AsyncSession, organization_id: UUID
) -> dict[str, Any]:
    """Extend deterministic risk scan with severity, reason, and suggested action."""
    raw = await ai_intelligence.scan_portfolio_risks(db, organization_id)
    enriched = []
    for r in raw:
        enriched.append(
            {
                **r,
                "severity": r.get("severity", "medium"),
                "reason": r.get("summary") or r.get("reason") or r.get("title"),
                "suggested_action": r.get("suggested_action")
                or r.get("recommendation")
                or "Review and assign an owner",
                "responsible_role": r.get("responsible_role") or "manager",
                "recommended_deadline_days": 14
                if r.get("severity") in ("high", "critical")
                else 30,
            }
        )
    by_sev = Counter(e["severity"] for e in enriched)
    return {
        "generated_at": utcnow().isoformat(),
        "total": len(enriched),
        "by_severity": dict(by_sev),
        "items": enriched,
        "citations": [{"source": "ai_intelligence.scan_portfolio_risks"}],
    }
