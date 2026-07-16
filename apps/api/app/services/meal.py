from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.evaluation import Evaluation
from app.models.indicator import Indicator, IndicatorTarget
from app.models.logframe import Logframe, LogframeResult
from app.models.monitoring import MonitoringResult
from app.models.program import Program
from app.models.project import Project
from app.models.theory_of_change import TheoryOfChange
from app.services.audit import write_audit_log
from app.services.programs import make_code, _ensure_unique_code


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


# -------- Theory of Change --------


async def get_toc(db: AsyncSession, organization_id: UUID, toc_id: UUID) -> TheoryOfChange:
    toc = await db.scalar(
        select(TheoryOfChange).where(
            TheoryOfChange.id == toc_id, TheoryOfChange.organization_id == organization_id
        )
    )
    if not toc:
        raise NotFoundError("Theory of Change not found")
    return toc


async def list_tocs(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[TheoryOfChange], int]:
    filters = [TheoryOfChange.organization_id == organization_id]
    if status:
        filters.append(TheoryOfChange.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((TheoryOfChange.name.ilike(like)) | (TheoryOfChange.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(TheoryOfChange).where(*filters)) or 0
    result = await db.execute(
        select(TheoryOfChange)
        .where(*filters)
        .order_by(TheoryOfChange.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_toc(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TheoryOfChange:
    await _assert_links(db, organization_id, data)
    code = await _ensure_unique_code(
        db,
        model=TheoryOfChange,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="TOC-"),
    )
    toc = TheoryOfChange(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        name=data["name"].strip(),
        code=code,
        status=data.get("status") or "draft",
        goal_statement=data.get("goal_statement"),
        problem_statement=data.get("problem_statement"),
        assumptions=data.get("assumptions"),
        success_criteria=data.get("success_criteria"),
        pathways=data.get("pathways") or [],
        created_by_id=actor_id,
    )
    db.add(toc)
    await db.flush()
    await write_audit_log(
        db,
        action="theories_of_change.create",
        resource_type="theory_of_change",
        resource_id=toc.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created theory of change {toc.code}",
        changes={"name": toc.name, "code": toc.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return toc


async def update_toc(
    db: AsyncSession,
    toc: TheoryOfChange,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TheoryOfChange:
    await _assert_links(db, toc.organization_id, data)
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="TOC-")
        if new_code != toc.code:
            data["code"] = await _ensure_unique_code(
                db, model=TheoryOfChange, organization_id=toc.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(toc, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="theories_of_change.update",
        resource_type="theory_of_change",
        resource_id=toc.id,
        organization_id=toc.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated theory of change {toc.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return toc


async def delete_toc(
    db: AsyncSession,
    toc: TheoryOfChange,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="theories_of_change.delete",
        resource_type="theory_of_change",
        resource_id=toc.id,
        organization_id=toc.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted theory of change {toc.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(toc)
    await db.flush()


# -------- Logframes --------


async def get_logframe(db: AsyncSession, organization_id: UUID, logframe_id: UUID) -> Logframe:
    logframe = await db.scalar(
        select(Logframe)
        .options(selectinload(Logframe.results))
        .where(Logframe.id == logframe_id, Logframe.organization_id == organization_id)
    )
    if not logframe:
        raise NotFoundError("Logframe not found")
    return logframe


async def list_logframes(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Logframe], int]:
    filters = [Logframe.organization_id == organization_id]
    if status:
        filters.append(Logframe.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Logframe.name.ilike(like)) | (Logframe.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Logframe).where(*filters)) or 0
    result = await db.execute(
        select(Logframe)
        .options(selectinload(Logframe.results))
        .where(*filters)
        .order_by(Logframe.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def create_logframe(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Logframe:
    await _assert_links(db, organization_id, data)
    if data.get("theory_of_change_id"):
        await get_toc(db, organization_id, data["theory_of_change_id"])
    code = await _ensure_unique_code(
        db,
        model=Logframe,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="LF-"),
    )
    results_data = data.pop("results", None) or []
    logframe = Logframe(
        organization_id=organization_id,
        theory_of_change_id=data.get("theory_of_change_id"),
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        status=data.get("status") or "draft",
        created_by_id=actor_id,
    )
    db.add(logframe)
    await db.flush()
    for idx, row in enumerate(results_data):
        db.add(
            LogframeResult(
                organization_id=organization_id,
                logframe_id=logframe.id,
                parent_id=row.get("parent_id"),
                level=row["level"],
                code=row.get("code"),
                statement=row["statement"],
                assumptions=row.get("assumptions"),
                means_of_verification=row.get("means_of_verification"),
                sort_order=row.get("sort_order", idx),
            )
        )
    await db.flush()
    await write_audit_log(
        db,
        action="logframes.create",
        resource_type="logframe",
        resource_id=logframe.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created logframe {logframe.code}",
        changes={"name": logframe.name, "code": logframe.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_logframe(db, organization_id, logframe.id)


async def update_logframe(
    db: AsyncSession,
    logframe: Logframe,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Logframe:
    await _assert_links(db, logframe.organization_id, data)
    if data.get("theory_of_change_id"):
        await get_toc(db, logframe.organization_id, data["theory_of_change_id"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="LF-")
        if new_code != logframe.code:
            data["code"] = await _ensure_unique_code(
                db, model=Logframe, organization_id=logframe.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(logframe, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="logframes.update",
        resource_type="logframe",
        resource_id=logframe.id,
        organization_id=logframe.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated logframe {logframe.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_logframe(db, logframe.organization_id, logframe.id)


async def delete_logframe(
    db: AsyncSession,
    logframe: Logframe,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="logframes.delete",
        resource_type="logframe",
        resource_id=logframe.id,
        organization_id=logframe.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted logframe {logframe.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(logframe)
    await db.flush()


async def add_logframe_result(
    db: AsyncSession,
    logframe: Logframe,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> LogframeResult:
    if data.get("parent_id"):
        parent = await db.scalar(
            select(LogframeResult).where(
                LogframeResult.id == data["parent_id"],
                LogframeResult.logframe_id == logframe.id,
                LogframeResult.organization_id == logframe.organization_id,
            )
        )
        if not parent:
            raise NotFoundError("Parent logframe result not found")
    result = LogframeResult(
        organization_id=logframe.organization_id,
        logframe_id=logframe.id,
        parent_id=data.get("parent_id"),
        level=data["level"],
        code=data.get("code"),
        statement=data["statement"],
        assumptions=data.get("assumptions"),
        means_of_verification=data.get("means_of_verification"),
        sort_order=data.get("sort_order") or 0,
    )
    db.add(result)
    await db.flush()
    await write_audit_log(
        db,
        action="logframes.results.create",
        resource_type="logframe_result",
        resource_id=result.id,
        organization_id=logframe.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added {result.level} result to {logframe.code}",
        changes={"level": result.level, "statement": result.statement},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


# -------- Indicators --------


async def get_indicator(
    db: AsyncSession, organization_id: UUID, indicator_id: UUID
) -> Indicator:
    indicator = await db.scalar(
        select(Indicator)
        .options(selectinload(Indicator.targets))
        .where(Indicator.id == indicator_id, Indicator.organization_id == organization_id)
    )
    if not indicator:
        raise NotFoundError("Indicator not found")
    return indicator


async def list_indicators(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Indicator], int]:
    filters = [Indicator.organization_id == organization_id]
    if status:
        filters.append(Indicator.status == status)
    if level:
        filters.append(Indicator.level == level)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Indicator.name.ilike(like)) | (Indicator.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Indicator).where(*filters)) or 0
    result = await db.execute(
        select(Indicator)
        .options(selectinload(Indicator.targets))
        .where(*filters)
        .order_by(Indicator.code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def create_indicator(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Indicator:
    await _assert_links(db, organization_id, data)
    if data.get("logframe_result_id"):
        result = await db.scalar(
            select(LogframeResult).where(
                LogframeResult.id == data["logframe_result_id"],
                LogframeResult.organization_id == organization_id,
            )
        )
        if not result:
            raise NotFoundError("Logframe result not found")
    targets_data = data.pop("targets", None) or []
    code = await _ensure_unique_code(
        db,
        model=Indicator,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="IND-"),
    )
    indicator = Indicator(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        logframe_result_id=data.get("logframe_result_id"),
        activity_id=data.get("activity_id"),
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        level=data.get("level") or "outcome",
        measure_type=data.get("measure_type") or "quantitative",
        unit=data.get("unit"),
        direction=data.get("direction") or "increase",
        collection_method=data.get("collection_method"),
        frequency=data.get("frequency"),
        baseline_value=_dec(data.get("baseline_value")),
        baseline_date=data.get("baseline_date"),
        status=data.get("status") or "active",
        disaggregation=data.get("disaggregation") or {},
        created_by_id=actor_id,
    )
    db.add(indicator)
    await db.flush()
    for target in targets_data:
        db.add(
            IndicatorTarget(
                organization_id=organization_id,
                indicator_id=indicator.id,
                period_label=target["period_label"],
                start_date=target.get("start_date"),
                end_date=target.get("end_date"),
                target_value=_dec(target.get("target_value")) or Decimal("0"),
                notes=target.get("notes"),
                status=target.get("status") or "planned",
            )
        )
    await db.flush()
    await write_audit_log(
        db,
        action="indicators.create",
        resource_type="indicator",
        resource_id=indicator.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created indicator {indicator.code}",
        changes={"name": indicator.name, "code": indicator.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_indicator(db, organization_id, indicator.id)


async def update_indicator(
    db: AsyncSession,
    indicator: Indicator,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Indicator:
    await _assert_links(db, indicator.organization_id, data)
    if "baseline_value" in data:
        data["baseline_value"] = _dec(data["baseline_value"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="IND-")
        if new_code != indicator.code:
            data["code"] = await _ensure_unique_code(
                db, model=Indicator, organization_id=indicator.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(indicator, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="indicators.update",
        resource_type="indicator",
        resource_id=indicator.id,
        organization_id=indicator.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated indicator {indicator.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_indicator(db, indicator.organization_id, indicator.id)


async def delete_indicator(
    db: AsyncSession,
    indicator: Indicator,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="indicators.delete",
        resource_type="indicator",
        resource_id=indicator.id,
        organization_id=indicator.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted indicator {indicator.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(indicator)
    await db.flush()


async def add_indicator_target(
    db: AsyncSession,
    indicator: Indicator,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> IndicatorTarget:
    target = IndicatorTarget(
        organization_id=indicator.organization_id,
        indicator_id=indicator.id,
        period_label=data["period_label"],
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        target_value=_dec(data.get("target_value")) or Decimal("0"),
        notes=data.get("notes"),
        status=data.get("status") or "planned",
    )
    db.add(target)
    await db.flush()
    await write_audit_log(
        db,
        action="indicators.targets.create",
        resource_type="indicator_target",
        resource_id=target.id,
        organization_id=indicator.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added target {target.period_label} to {indicator.code}",
        changes={"period_label": target.period_label, "target_value": str(target.target_value)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return target


# -------- Monitoring --------


async def get_monitoring_result(
    db: AsyncSession, organization_id: UUID, result_id: UUID
) -> MonitoringResult:
    result = await db.scalar(
        select(MonitoringResult).where(
            MonitoringResult.id == result_id,
            MonitoringResult.organization_id == organization_id,
        )
    )
    if not result:
        raise NotFoundError("Monitoring result not found")
    return result


async def list_monitoring_results(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    indicator_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> tuple[list[MonitoringResult], int]:
    filters = [MonitoringResult.organization_id == organization_id]
    if indicator_id:
        filters.append(MonitoringResult.indicator_id == indicator_id)
    if status:
        filters.append(MonitoringResult.status == status)
    total = await db.scalar(select(func.count()).select_from(MonitoringResult).where(*filters)) or 0
    result = await db.execute(
        select(MonitoringResult)
        .where(*filters)
        .order_by(MonitoringResult.reporting_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_monitoring_result(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MonitoringResult:
    indicator = await get_indicator(db, organization_id, data["indicator_id"])
    if data.get("project_id"):
        await _assert_project(db, organization_id, data["project_id"])
    if data.get("target_id"):
        target = await db.scalar(
            select(IndicatorTarget).where(
                IndicatorTarget.id == data["target_id"],
                IndicatorTarget.indicator_id == indicator.id,
                IndicatorTarget.organization_id == organization_id,
            )
        )
        if not target:
            raise NotFoundError("Indicator target not found")
    result = MonitoringResult(
        organization_id=organization_id,
        indicator_id=indicator.id,
        target_id=data.get("target_id"),
        project_id=data.get("project_id"),
        reporting_date=data["reporting_date"],
        period_start=data.get("period_start"),
        period_end=data.get("period_end"),
        actual_value=_dec(data.get("actual_value")),
        qualitative_value=data.get("qualitative_value"),
        status=data.get("status") or "draft",
        data_source=data.get("data_source"),
        location_label=data.get("location_label"),
        notes=data.get("notes"),
        collected_by_id=actor_id,
        created_by_id=actor_id,
    )
    db.add(result)
    await db.flush()
    await write_audit_log(
        db,
        action="monitoring.create",
        resource_type="monitoring_result",
        resource_id=result.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Recorded monitoring result for {indicator.code}",
        changes={
            "indicator_id": str(indicator.id),
            "actual_value": str(result.actual_value) if result.actual_value is not None else None,
            "status": result.status,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


async def update_monitoring_result(
    db: AsyncSession,
    result: MonitoringResult,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> MonitoringResult:
    if "actual_value" in data:
        data["actual_value"] = _dec(data["actual_value"])
    if data.get("status") == "verified":
        data["verified_by_id"] = actor_id
    for key, value in data.items():
        setattr(result, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="monitoring.update",
        resource_type="monitoring_result",
        resource_id=result.id,
        organization_id=result.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description="Updated monitoring result",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


async def delete_monitoring_result(
    db: AsyncSession,
    result: MonitoringResult,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="monitoring.delete",
        resource_type="monitoring_result",
        resource_id=result.id,
        organization_id=result.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description="Deleted monitoring result",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(result)
    await db.flush()


# -------- Evaluations --------


async def get_evaluation(
    db: AsyncSession, organization_id: UUID, evaluation_id: UUID
) -> Evaluation:
    evaluation = await db.scalar(
        select(Evaluation).where(
            Evaluation.id == evaluation_id, Evaluation.organization_id == organization_id
        )
    )
    if not evaluation:
        raise NotFoundError("Evaluation not found")
    return evaluation


async def list_evaluations(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    evaluation_type: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Evaluation], int]:
    filters = [Evaluation.organization_id == organization_id]
    if status:
        filters.append(Evaluation.status == status)
    if evaluation_type:
        filters.append(Evaluation.evaluation_type == evaluation_type)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Evaluation.name.ilike(like)) | (Evaluation.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Evaluation).where(*filters)) or 0
    result = await db.execute(
        select(Evaluation)
        .where(*filters)
        .order_by(Evaluation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_evaluation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Evaluation:
    await _assert_links(db, organization_id, data)
    code = await _ensure_unique_code(
        db,
        model=Evaluation,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="EVAL-"),
    )
    evaluation = Evaluation(
        organization_id=organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        name=data["name"].strip(),
        code=code,
        evaluation_type=data.get("evaluation_type") or "midline",
        status=data.get("status") or "planned",
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        evaluator_name=data.get("evaluator_name"),
        objectives=data.get("objectives"),
        methodology=data.get("methodology"),
        key_findings=data.get("key_findings"),
        recommendations=data.get("recommendations"),
        lessons_learned=data.get("lessons_learned"),
        created_by_id=actor_id,
    )
    db.add(evaluation)
    await db.flush()
    await write_audit_log(
        db,
        action="evaluations.create",
        resource_type="evaluation",
        resource_id=evaluation.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created evaluation {evaluation.code}",
        changes={"name": evaluation.name, "code": evaluation.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return evaluation


async def update_evaluation(
    db: AsyncSession,
    evaluation: Evaluation,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Evaluation:
    await _assert_links(db, evaluation.organization_id, data)
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="EVAL-")
        if new_code != evaluation.code:
            data["code"] = await _ensure_unique_code(
                db, model=Evaluation, organization_id=evaluation.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(evaluation, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="evaluations.update",
        resource_type="evaluation",
        resource_id=evaluation.id,
        organization_id=evaluation.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated evaluation {evaluation.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return evaluation


async def delete_evaluation(
    db: AsyncSession,
    evaluation: Evaluation,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="evaluations.delete",
        resource_type="evaluation",
        resource_id=evaluation.id,
        organization_id=evaluation.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted evaluation {evaluation.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(evaluation)
    await db.flush()


async def phase4_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    tocs = await db.scalar(
        select(func.count())
        .select_from(TheoryOfChange)
        .where(TheoryOfChange.organization_id == organization_id)
    )
    logframes = await db.scalar(
        select(func.count()).select_from(Logframe).where(Logframe.organization_id == organization_id)
    )
    indicators = await db.scalar(
        select(func.count())
        .select_from(Indicator)
        .where(Indicator.organization_id == organization_id)
    )
    active_indicators = await db.scalar(
        select(func.count())
        .select_from(Indicator)
        .where(Indicator.organization_id == organization_id, Indicator.status == "active")
    )
    monitoring = await db.scalar(
        select(func.count())
        .select_from(MonitoringResult)
        .where(MonitoringResult.organization_id == organization_id)
    )
    evaluations = await db.scalar(
        select(func.count())
        .select_from(Evaluation)
        .where(Evaluation.organization_id == organization_id)
    )
    return {
        "theories_of_change_count": tocs or 0,
        "logframes_count": logframes or 0,
        "indicators_count": indicators or 0,
        "active_indicators_count": active_indicators or 0,
        "monitoring_results_count": monitoring or 0,
        "evaluations_count": evaluations or 0,
    }
