"""Deterministic portfolio intelligence (no ML).

These helpers turn the raw domain data into risk signals, dashboard insights,
and grounded structured reports. Everything is rule-based so it works with or
without an OpenAI key; the ai_provider is only used to phrase narratives around
numbers that are computed here.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow

_BEHIND_THRESHOLD = 70.0
_BURN_THRESHOLD = 0.85
_GRANT_WINDOW_DAYS = 90


def _severity_for_pct(progress_pct: Optional[float]) -> str:
    if progress_pct is None:
        return "medium"
    if progress_pct < 40:
        return "high"
    if progress_pct < _BEHIND_THRESHOLD:
        return "medium"
    return "low"


async def scan_portfolio_risks(db: AsyncSession, organization_id: UUID) -> list[dict[str, Any]]:
    """Rule-based scan of the portfolio returning risk signal dicts."""
    from app.models.grant import Grant
    from app.models.prediction import AiPrediction
    from app.models.survey import Survey, SurveyResponse
    from app.models.task import Task
    from app.services import finance as finance_service
    from app.services import meal as meal_service

    risks: list[dict[str, Any]] = []
    today = date.today()

    # 1) Overdue tasks (open + due date in the past)
    overdue_total = (
        await db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.organization_id == organization_id,
                Task.status.notin_(["done", "cancelled"]),
                Task.due_date.is_not(None),
                Task.due_date < today,
            )
        )
    ) or 0
    if overdue_total:
        risks.append(
            {
                "type": "overdue_tasks",
                "title": f"{overdue_total} overdue task(s)",
                "severity": "high" if overdue_total >= 10 else "medium",
                "summary": (
                    f"{overdue_total} open task(s) are past their due date. "
                    "Reassign or reschedule to protect delivery timelines."
                ),
                "metric": {"overdue_tasks": overdue_total},
                "recommendation": "Triage overdue tasks and confirm blockers with owners.",
            }
        )

    # 2) Indicators behind target (progress < 70%)
    progress = await meal_service.indicator_progress(db, organization_id, limit=100)
    behind = [
        row
        for row in progress
        if row.get("progress_pct") is not None and row["progress_pct"] < _BEHIND_THRESHOLD
    ]
    for row in behind:
        risks.append(
            {
                "type": "indicator_behind",
                "title": f"Indicator behind: {row['name']}",
                "severity": _severity_for_pct(row.get("progress_pct")),
                "summary": (
                    f"{row['name']} is at {row['progress_pct']}% of target "
                    f"({row.get('actual_value')}/{row.get('target_value')})."
                ),
                "metric": {
                    "indicator_id": row.get("indicator_id"),
                    "progress_pct": row.get("progress_pct"),
                },
                "recommendation": "Increase monitoring cadence and verify data capture.",
            }
        )

    # 3) Grants ending within 90 days
    horizon = today + timedelta(days=_GRANT_WINDOW_DAYS)
    ending_grants = list(
        await db.scalars(
            select(Grant).where(
                Grant.organization_id == organization_id,
                Grant.end_date.is_not(None),
                Grant.end_date >= today,
                Grant.end_date <= horizon,
                Grant.status.in_(["awarded", "active"]),
            )
        )
    )
    for g in ending_grants:
        risks.append(
            {
                "type": "grant_ending",
                "title": f"Grant ending soon: {g.name}",
                "severity": "medium",
                "summary": f"Grant '{g.name}' ends on {g.end_date} (within {_GRANT_WINDOW_DAYS} days).",
                "metric": {"grant_id": str(g.id), "end_date": str(g.end_date)},
                "recommendation": "Plan close-out reporting and any no-cost extension early.",
            }
        )

    # 4) Budget burn > 85%
    counts = await finance_service.phase3_counts(db, organization_id)
    awarded = Decimal(str(counts.get("grants_awarded_total") or 0))
    expenses = Decimal(str(counts.get("expenses_total") or 0))
    if awarded > 0:
        burn = float(expenses / awarded)
        if burn > _BURN_THRESHOLD:
            risks.append(
                {
                    "type": "budget_burn",
                    "title": f"High budget burn ({burn * 100:.0f}%)",
                    "severity": "high" if burn > 0.95 else "medium",
                    "summary": (
                        f"Posted expenses are {burn * 100:.0f}% of awarded funding "
                        f"({expenses}/{awarded})."
                    ),
                    "metric": {"burn_ratio": round(burn, 3)},
                    "recommendation": "Review remaining budget lines against forecast to period end.",
                }
            )

    # 5) Published surveys with zero responses
    published_surveys = list(
        await db.scalars(
            select(Survey).where(
                Survey.organization_id == organization_id,
                Survey.status == "published",
            )
        )
    )
    for s in published_surveys:
        response_count = (
            await db.scalar(
                select(func.count())
                .select_from(SurveyResponse)
                .where(
                    SurveyResponse.organization_id == organization_id,
                    SurveyResponse.survey_id == s.id,
                )
            )
        ) or 0
        if response_count == 0:
            risks.append(
                {
                    "type": "survey_no_responses",
                    "title": f"No responses: {s.name}",
                    "severity": "low",
                    "summary": f"Published survey '{s.name}' has no responses yet.",
                    "metric": {"survey_id": str(s.id)},
                    "recommendation": "Assign the survey to field officers or check distribution.",
                }
            )

    # 6) Open high-severity predictions
    open_high = list(
        await db.scalars(
            select(AiPrediction).where(
                AiPrediction.organization_id == organization_id,
                AiPrediction.status == "open",
                AiPrediction.severity.in_(["high", "critical"]),
            )
        )
    )
    for p in open_high:
        risks.append(
            {
                "type": "open_prediction",
                "title": f"Open risk: {p.title}",
                "severity": p.severity,
                "summary": (p.summary or "")[:300],
                "metric": {"prediction_id": str(p.id), "score": str(p.score)},
                "recommendation": "Review the prediction and mark it resolved once mitigated.",
            }
        )

    return risks


async def build_dashboard_insights(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    """Assemble a grounded dashboard insight payload from deterministic signals."""
    from app.services import ai as ai_service
    from app.services import meal as meal_service

    snapshot = await ai_service._org_snapshot(db, organization_id)
    risks = await scan_portfolio_risks(db, organization_id)
    progress = await meal_service.indicator_progress(db, organization_id, limit=100)

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    key_risks = sorted(risks, key=lambda r: severity_rank.get(r.get("severity", "low"), 3))[:5]

    key_wins: list[dict[str, Any]] = []
    for row in progress:
        pct = row.get("progress_pct")
        if pct is not None and pct >= 100:
            key_wins.append(
                {
                    "title": f"{row['name']} target met",
                    "detail": f"{row['name']} reached {pct}% of target.",
                    "indicator_id": row.get("indicator_id"),
                }
            )
    if not key_wins:
        active_grants = snapshot.get("active_grants_count") or 0
        if active_grants:
            key_wins.append(
                {
                    "title": "Active funding secured",
                    "detail": f"{active_grants} grant(s) are active or awarded.",
                }
            )

    recommendations = [r["recommendation"] for r in key_risks if r.get("recommendation")]
    if not recommendations:
        recommendations = ["Maintain monitoring cadence and keep evidence up to date."]

    upcoming_actions = [
        {"title": r["title"], "severity": r["severity"], "action": r.get("recommendation")}
        for r in key_risks
        if r["type"] in ("overdue_tasks", "grant_ending", "indicator_behind")
    ]

    high_count = sum(1 for r in risks if r.get("severity") in ("high", "critical"))
    summary = (
        f"Portfolio scan found {len(risks)} risk signal(s) "
        f"({high_count} high/critical). "
        f"Tracking {snapshot.get('indicators_count', 0)} indicator(s) across "
        f"{snapshot.get('projects_count', 0)} project(s)."
    )

    return {
        "summary": summary,
        "key_risks": key_risks,
        "key_wins": key_wins,
        "recommendations": recommendations[:5],
        "upcoming_actions": upcoming_actions,
        "predictions": risks,
        "generated_at": utcnow().isoformat(),
    }


_REPORT_TYPES = {
    "monthly",
    "quarterly",
    "annual",
    "board",
    "donor",
    "project_status",
    "activity",
    "indicator",
    "executive_brief",
    "lessons_learned",
    "success_story",
    "risk_analysis",
}


async def generate_structured_report(
    db: AsyncSession,
    organization_id: UUID,
    report_type: str,
    *,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    permissions: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Produce a markdown report grounded in real portfolio data.

    The numbers are always computed deterministically; the AI provider is only
    asked to phrase a narrative around the supplied, real context.
    """
    from app.services import ai as ai_service
    from app.services import ai_provider
    from app.services import meal as meal_service

    rtype = report_type if report_type in _REPORT_TYPES else "monthly"
    snapshot = await ai_service._org_snapshot(db, organization_id)
    progress = await meal_service.indicator_progress(db, organization_id, limit=25)
    risks = await scan_portfolio_risks(db, organization_id)

    context: dict[str, Any] = {
        "report_type": rtype,
        "snapshot": snapshot,
        "indicator_progress": progress,
        "risk_signals": risks,
    }
    if program_id:
        context["program_id"] = str(program_id)
    if project_id:
        context["project_id"] = str(project_id)

    title = f"{rtype.replace('_', ' ').title()} Report"

    narrative = await ai_provider.generate_narrative_text(
        rtype,
        context,
        prompt=(
            f"Write the narrative body of a {rtype.replace('_', ' ')} report for an NGO. "
            "Use ONLY the numbers in this context; never invent figures. "
            f"Context JSON:\n{context}"
        ),
    )

    behind = [r for r in progress if r.get("progress_pct") is not None and r["progress_pct"] < 70]
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"_Generated {utcnow().date().isoformat()}_")
    lines.append("")
    lines.append("## Portfolio snapshot")
    lines.append("")
    lines.append(f"- Programs: {snapshot.get('programs_count', 0)}")
    lines.append(f"- Projects: {snapshot.get('projects_count', 0)}")
    lines.append(f"- Open tasks: {snapshot.get('open_tasks_count', 0)}")
    lines.append(f"- Active grants: {snapshot.get('active_grants_count', 0)}")
    lines.append(f"- Beneficiaries reached: {snapshot.get('beneficiaries_count', 0)}")
    lines.append("")
    lines.append("## Narrative")
    lines.append("")
    lines.append(narrative["content"])
    lines.append("")
    if progress:
        lines.append("## Indicator progress")
        lines.append("")
        for row in progress[:15]:
            pct = row.get("progress_pct")
            pct_str = f"{pct}%" if pct is not None else "n/a"
            lines.append(f"- {row['name']}: {pct_str} ({row.get('actual_value')}/{row.get('target_value')})")
        lines.append("")
    if behind:
        lines.append("## Indicators behind target")
        lines.append("")
        for row in behind[:10]:
            lines.append(f"- {row['name']} ({row['progress_pct']}% of target)")
        lines.append("")
    if risks:
        lines.append("## Key risks")
        lines.append("")
        for r in risks[:10]:
            lines.append(f"- **[{r['severity']}]** {r['title']} — {r.get('summary', '')}")
        lines.append("")

    content = "\n".join(lines)
    return {
        "report_type": rtype,
        "title": title,
        "content": content,
        "provider": narrative["provider"],
        "model": narrative.get("model"),
        "generated_at": utcnow().isoformat(),
        "context": context,
    }
