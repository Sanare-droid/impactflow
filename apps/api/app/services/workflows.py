"""Workflow automation engine: CRUD, event matching, execution, approvals, schedules.

Design constraints (V1.3 Epic 3):
- Hooks into the existing ``emit_event`` fan-out and the ``run_job_tick`` loop;
  it never spins up a second job loop, event bus, or notification stack.
- Actions reuse existing services only (notifications, events/webhooks, mailer,
  audit, AI drafting). AI may draft workflow JSON but workflows are never
  executed from AI tools.
- Every query is scoped by ``organization_id``; cross-tenant access raises
  ``NotFoundError``.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.db.base import utcnow
from app.models.membership import OrganizationMembership
from app.models.role import Role
from app.models.task import Task
from app.models.user import User
from app.models.workflow import (
    Workflow,
    WorkflowApproval,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowSchedule,
    WorkflowVersion,
)
from app.services import events as events_service
from app.services import notifications as notification_service
from app.services import workflow_schema
from app.services.audit import write_audit_log
from app.services.programs import _ensure_unique_code, make_code

BACKOFF_SECONDS = [30, 120, 300, 900, 3600]

CADENCE_DELTAS: dict[str, timedelta] = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=90),
    "annually": timedelta(days=365),
}

_INTERP_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_path(path: str, source: dict[str, Any]) -> Any:
    current: Any = source
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _interp_source(
    *, organization_id: UUID, payload: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "trigger": payload or {},
        "context": context or {},
        "org": {"id": str(organization_id)},
        "now": utcnow().isoformat(),
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            source.setdefault(key, value)
    return source


def _interpolate(value: Any, source: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def _replace(match: "re.Match[str]") -> str:
            resolved = _resolve_path(match.group(1), source)
            return "" if resolved is None else str(resolved)

        return _INTERP_RE.sub(_replace, value)
    if isinstance(value, list):
        return [_interpolate(v, source) for v in value]
    if isinstance(value, dict):
        return {k: _interpolate(v, source) for k, v in value.items()}
    return value


async def get_workflow(db: AsyncSession, organization_id: UUID, workflow_id: UUID) -> Workflow:
    row = await db.scalar(
        select(Workflow).where(
            Workflow.id == workflow_id, Workflow.organization_id == organization_id
        )
    )
    if not row:
        raise NotFoundError("Workflow not found")
    return row


async def _current_version(db: AsyncSession, workflow: Workflow) -> WorkflowVersion:
    row = await db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.version == workflow.current_version,
        )
    )
    if not row:
        raise NotFoundError("Workflow version not found")
    return row


# --------------------------------------------------------------------------- #
# Workflow CRUD
# --------------------------------------------------------------------------- #


async def list_workflows(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    is_template: Optional[bool] = None,
    search: Optional[str] = None,
) -> tuple[list[Workflow], int]:
    filters = [Workflow.organization_id == organization_id]
    if status:
        filters.append(Workflow.status == status)
    if category:
        filters.append(Workflow.category == category)
    if is_template is not None:
        filters.append(Workflow.is_template == is_template)
    if search:
        like = f"%{search.strip()}%"
        filters.append(Workflow.name.ilike(like))
    total = await db.scalar(select(func.count()).select_from(Workflow).where(*filters)) or 0
    rows = await db.scalars(
        select(Workflow)
        .where(*filters)
        .order_by(Workflow.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def create_workflow(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: Optional[str] = None,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Workflow:
    definition = workflow_schema.normalize_definition(data.get("definition"))
    workflow_schema.validate_definition(definition)

    code = await _ensure_unique_code(
        db,
        model=Workflow,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="WF-"),
    )
    workflow = Workflow(
        organization_id=organization_id,
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        category=data.get("category"),
        status=data.get("status") or "draft",
        current_version=1,
        is_template=bool(data.get("is_template") or False),
        created_by_id=actor_id,
        metadata_=data.get("metadata") or {},
    )
    db.add(workflow)
    await db.flush()

    version = WorkflowVersion(
        organization_id=organization_id,
        workflow_id=workflow.id,
        version=1,
        title=workflow.name,
        definition_=definition,
        changelog=data.get("changelog"),
        created_by_id=actor_id,
    )
    if workflow.status == "active":
        version.published_at = utcnow()
    db.add(version)
    await db.flush()

    await write_audit_log(
        db,
        action="workflows.create",
        resource_type="workflow",
        resource_id=workflow.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created workflow {workflow.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return workflow


async def update_workflow(
    db: AsyncSession,
    workflow: Workflow,
    *,
    actor_id: UUID,
    actor_email: Optional[str] = None,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Workflow:
    definition = data.pop("definition", None)
    changelog = data.pop("changelog", None)

    for key in ("name", "description", "category", "status", "is_template"):
        if key in data and data[key] is not None:
            setattr(workflow, key, data[key])
    if data.get("metadata") is not None:
        workflow.metadata_ = data["metadata"]

    if definition is not None:
        await save_definition(
            db, workflow, definition=definition, actor_id=actor_id, changelog=changelog
        )

    await db.flush()
    await write_audit_log(
        db,
        action="workflows.update",
        resource_type="workflow",
        resource_id=workflow.id,
        organization_id=workflow.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated workflow {workflow.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return workflow


async def save_definition(
    db: AsyncSession,
    workflow: Workflow,
    *,
    definition: dict,
    actor_id: UUID,
    changelog: Optional[str] = None,
) -> WorkflowVersion:
    """Persist a new immutable definition version (bumps ``current_version``)."""
    normalized = workflow_schema.normalize_definition(definition)
    workflow_schema.validate_definition(normalized)

    next_version = workflow.current_version + 1
    version = WorkflowVersion(
        organization_id=workflow.organization_id,
        workflow_id=workflow.id,
        version=next_version,
        title=workflow.name,
        definition_=normalized,
        changelog=changelog,
        created_by_id=actor_id,
    )
    workflow.current_version = next_version
    db.add(version)
    await db.flush()
    return version


async def activate_workflow(
    db: AsyncSession,
    workflow: Workflow,
    *,
    actor_id: UUID,
    actor_email: Optional[str] = None,
) -> Workflow:
    version = await _current_version(db, workflow)
    workflow_schema.validate_definition(version.definition_)
    workflow.status = "active"
    if not version.published_at:
        version.published_at = utcnow()
    await db.flush()
    await write_audit_log(
        db,
        action="workflows.activate",
        resource_type="workflow",
        resource_id=workflow.id,
        organization_id=workflow.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Activated workflow {workflow.code} v{version.version}",
    )
    return workflow


async def set_status(
    db: AsyncSession,
    workflow: Workflow,
    *,
    status: str,
    actor_id: UUID,
    actor_email: Optional[str] = None,
) -> Workflow:
    workflow.status = status
    await db.flush()
    await write_audit_log(
        db,
        action=f"workflows.{status}",
        resource_type="workflow",
        resource_id=workflow.id,
        organization_id=workflow.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Set workflow {workflow.code} status to {status}",
    )
    return workflow


async def enable_workflow(db, workflow, **kw):  # noqa: ANN001
    return await set_status(db, workflow, status="active", **kw)


async def disable_workflow(db, workflow, **kw):  # noqa: ANN001
    return await set_status(db, workflow, status="disabled", **kw)


async def archive_workflow(db, workflow, **kw):  # noqa: ANN001
    return await set_status(db, workflow, status="archived", **kw)


async def clone_workflow(
    db: AsyncSession,
    workflow: Workflow,
    *,
    actor_id: UUID,
    actor_email: Optional[str] = None,
    name: Optional[str] = None,
) -> Workflow:
    source_version = await _current_version(db, workflow)
    return await _clone_from_definition(
        db,
        organization_id=workflow.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        name=name or f"{workflow.name} (Copy)",
        category=workflow.category,
        description=workflow.description,
        definition=source_version.definition_,
        cloned_from_id=workflow.id,
    )


async def _clone_from_definition(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: Optional[str],
    name: str,
    category: Optional[str],
    description: Optional[str],
    definition: dict,
    cloned_from_id: Optional[UUID] = None,
) -> Workflow:
    code = await _ensure_unique_code(
        db,
        model=Workflow,
        organization_id=organization_id,
        code=make_code(name, prefix="WF-"),
    )
    clone = Workflow(
        organization_id=organization_id,
        name=name,
        code=code,
        description=description,
        category=category,
        status="draft",
        current_version=1,
        is_template=False,
        cloned_from_id=cloned_from_id,
        created_by_id=actor_id,
        metadata_={},
    )
    db.add(clone)
    await db.flush()

    normalized = workflow_schema.normalize_definition(definition)
    version = WorkflowVersion(
        organization_id=organization_id,
        workflow_id=clone.id,
        version=1,
        title=clone.name,
        definition_=normalized,
        created_by_id=actor_id,
    )
    db.add(version)
    await db.flush()
    await write_audit_log(
        db,
        action="workflows.clone",
        resource_type="workflow",
        resource_id=clone.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Cloned workflow into {clone.code}",
        changes={"cloned_from_id": str(cloned_from_id) if cloned_from_id else None},
    )
    return clone


# --------------------------------------------------------------------------- #
# Versions & import/export
# --------------------------------------------------------------------------- #


async def list_versions(db: AsyncSession, workflow: Workflow) -> list[WorkflowVersion]:
    rows = await db.scalars(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow.id)
        .order_by(WorkflowVersion.version.desc())
    )
    return list(rows)


async def get_version(
    db: AsyncSession, organization_id: UUID, workflow_id: UUID, version: int
) -> WorkflowVersion:
    row = await db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.organization_id == organization_id,
            WorkflowVersion.version == version,
        )
    )
    if not row:
        raise NotFoundError("Workflow version not found")
    return row


async def export_definition(db: AsyncSession, workflow: Workflow) -> dict[str, Any]:
    version = await _current_version(db, workflow)
    return {
        "name": workflow.name,
        "code": workflow.code,
        "category": workflow.category,
        "description": workflow.description,
        "version": version.version,
        "definition": version.definition_,
    }


async def import_definition(
    db: AsyncSession,
    workflow: Workflow,
    *,
    definition: dict,
    actor_id: UUID,
    changelog: Optional[str] = None,
) -> WorkflowVersion:
    return await save_definition(
        db, workflow, definition=definition, actor_id=actor_id, changelog=changelog
    )


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #


async def list_templates(db: AsyncSession, organization_id: UUID) -> list[dict[str, Any]]:
    templates = workflow_schema.list_templates()
    db_templates = await db.scalars(
        select(Workflow).where(
            Workflow.organization_id == organization_id,
            Workflow.is_template.is_(True),
        )
    )
    for wf in db_templates:
        version = await _current_version(db, wf)
        templates.append(
            {
                "code": wf.code,
                "name": wf.name,
                "category": wf.category,
                "description": wf.description,
                "definition": version.definition_,
                "workflow_id": str(wf.id),
            }
        )
    return templates


async def clone_template(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: Optional[str] = None,
    template_code: str,
) -> Workflow:
    tpl = workflow_schema.get_template(template_code)
    if tpl:
        return await _clone_from_definition(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            actor_email=actor_email,
            name=tpl["name"],
            category=tpl.get("category"),
            description=tpl.get("description"),
            definition=tpl["definition"],
        )
    # Fall back to a DB-defined template by code
    db_tpl = await db.scalar(
        select(Workflow).where(
            Workflow.organization_id == organization_id,
            Workflow.code == template_code,
            Workflow.is_template.is_(True),
        )
    )
    if not db_tpl:
        raise NotFoundError("Template not found")
    return await clone_workflow(
        db, db_tpl, actor_id=actor_id, actor_email=actor_email, name=db_tpl.name
    )


# --------------------------------------------------------------------------- #
# Run creation & matching
# --------------------------------------------------------------------------- #


async def _create_run(
    db: AsyncSession,
    *,
    workflow: Workflow,
    version: WorkflowVersion,
    trigger_type: str,
    trigger_event: Optional[str],
    payload: dict[str, Any],
    context: Optional[dict[str, Any]] = None,
    actor_id: Optional[UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> WorkflowRun:
    definition = workflow_schema.normalize_definition(version.definition_)
    settings = definition.get("settings") or {}
    run = WorkflowRun(
        organization_id=workflow.organization_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status="pending",
        trigger_type=trigger_type,
        trigger_event=trigger_event,
        trigger_payload=payload or {},
        context=context or {},
        attempt_count=0,
        max_attempts=int(settings.get("max_attempts") or 5),
        next_attempt_at=utcnow(),
        created_by_id=actor_id,
        metadata_=metadata or {},
    )
    db.add(run)
    await db.flush()

    for idx, action in enumerate(definition["actions"]):
        db.add(
            WorkflowRunStep(
                organization_id=workflow.organization_id,
                run_id=run.id,
                step_index=idx,
                action_id=action["id"],
                action_type=action["type"],
                status="pending",
                input_json={
                    "config": action.get("config") or {},
                    "conditions": action.get("conditions"),
                    "name": action.get("name"),
                },
            )
        )
    await db.flush()
    return run


async def enqueue_matching_runs(
    db: AsyncSession,
    organization_id: UUID,
    event_type: str,
    payload: dict[str, Any],
    *,
    actor_id: Optional[UUID] = None,
) -> list[WorkflowRun]:
    """Create pending runs for active workflows whose trigger matches an event."""
    workflows = await db.scalars(
        select(Workflow).where(
            Workflow.organization_id == organization_id,
            Workflow.status == "active",
            Workflow.is_template.is_(False),
        )
    )
    created: list[WorkflowRun] = []
    payload_hash = _payload_hash(payload)
    for workflow in list(workflows):
        try:
            version = await _current_version(db, workflow)
        except NotFoundError:
            continue
        definition = workflow_schema.normalize_definition(version.definition_)
        trigger = definition.get("trigger") or {}
        trigger_type = trigger.get("type")
        aliases = workflow_schema.TRIGGER_ALIASES.get(trigger_type, [trigger_type])
        if event_type != trigger_type and event_type not in aliases:
            continue
        if not workflow_schema.evaluate_conditions(
            trigger.get("conditions"), payload, {}
        ):
            continue

        # Best-effort dedupe: skip identical event for same workflow within 60s.
        recent_runs = await db.scalars(
            select(WorkflowRun).where(
                WorkflowRun.workflow_id == workflow.id,
                WorkflowRun.trigger_event == event_type,
                WorkflowRun.created_at >= utcnow() - timedelta(seconds=60),
            )
        )
        if any((r.metadata_ or {}).get("payload_hash") == payload_hash for r in recent_runs):
            continue

        run = await _create_run(
            db,
            workflow=workflow,
            version=version,
            trigger_type="event",
            trigger_event=event_type,
            payload=payload,
            actor_id=actor_id,
            metadata={"payload_hash": payload_hash},
        )
        created.append(run)
    return created


async def enqueue_manual_run(
    db: AsyncSession,
    workflow: Workflow,
    *,
    actor_id: UUID,
    inputs: Optional[dict[str, Any]] = None,
) -> WorkflowRun:
    version = await _current_version(db, workflow)
    payload = {"event": "manual", "title": workflow.name, **(inputs or {})}
    return await _create_run(
        db,
        workflow=workflow,
        version=version,
        trigger_type="manual",
        trigger_event="manual",
        payload=payload,
        context={"inputs": inputs or {}},
        actor_id=actor_id,
    )


# --------------------------------------------------------------------------- #
# Schedules
# --------------------------------------------------------------------------- #


def _next_run_at(cadence: str, *, base: Optional[datetime] = None) -> datetime:
    now = base or utcnow()
    delta = CADENCE_DELTAS.get(cadence)
    if delta is None:
        # cron / unknown -> treat as daily for v1
        delta = CADENCE_DELTAS["daily"]
    return now + delta


async def list_schedules(
    db: AsyncSession, organization_id: UUID, workflow_id: UUID
) -> list[WorkflowSchedule]:
    rows = await db.scalars(
        select(WorkflowSchedule)
        .where(
            WorkflowSchedule.organization_id == organization_id,
            WorkflowSchedule.workflow_id == workflow_id,
        )
        .order_by(WorkflowSchedule.created_at.desc())
    )
    return list(rows)


async def get_schedule(
    db: AsyncSession, organization_id: UUID, schedule_id: UUID
) -> WorkflowSchedule:
    row = await db.scalar(
        select(WorkflowSchedule).where(
            WorkflowSchedule.id == schedule_id,
            WorkflowSchedule.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Schedule not found")
    return row


async def create_schedule(
    db: AsyncSession,
    workflow: Workflow,
    *,
    data: dict,
    actor_id: UUID,
) -> WorkflowSchedule:
    cadence = data.get("cadence") or "daily"
    row = WorkflowSchedule(
        organization_id=workflow.organization_id,
        workflow_id=workflow.id,
        cadence=cadence,
        cron_expr=data.get("cron_expr"),
        timezone=data.get("timezone") or "UTC",
        enabled=bool(data.get("enabled", True)),
        next_run_at=data.get("next_run_at") or _next_run_at(cadence),
        metadata_=data.get("metadata") or {},
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="workflows.schedule.create",
        resource_type="workflow_schedule",
        resource_id=row.id,
        organization_id=workflow.organization_id,
        actor_id=actor_id,
        description=f"Created {cadence} schedule for {workflow.code}",
    )
    return row


async def update_schedule(
    db: AsyncSession,
    schedule: WorkflowSchedule,
    *,
    data: dict,
    actor_id: UUID,
) -> WorkflowSchedule:
    for key in ("cadence", "cron_expr", "timezone", "enabled", "next_run_at"):
        if key in data and data[key] is not None:
            setattr(schedule, key, data[key])
    if data.get("metadata") is not None:
        schedule.metadata_ = data["metadata"]
    if data.get("cadence") and not data.get("next_run_at"):
        schedule.next_run_at = _next_run_at(schedule.cadence)
    await db.flush()
    await write_audit_log(
        db,
        action="workflows.schedule.update",
        resource_type="workflow_schedule",
        resource_id=schedule.id,
        organization_id=schedule.organization_id,
        actor_id=actor_id,
        description=f"Updated schedule {schedule.id}",
    )
    return schedule


async def delete_schedule(
    db: AsyncSession, schedule: WorkflowSchedule, *, actor_id: UUID
) -> None:
    await write_audit_log(
        db,
        action="workflows.schedule.delete",
        resource_type="workflow_schedule",
        resource_id=schedule.id,
        organization_id=schedule.organization_id,
        actor_id=actor_id,
        description=f"Deleted schedule {schedule.id}",
    )
    await db.delete(schedule)
    await db.flush()


async def process_due_schedules(db: AsyncSession) -> int:
    now = utcnow()
    schedules = await db.scalars(
        select(WorkflowSchedule).where(
            WorkflowSchedule.enabled.is_(True),
            WorkflowSchedule.next_run_at.is_not(None),
            WorkflowSchedule.next_run_at <= now,
        )
    )
    count = 0
    for schedule in list(schedules):
        workflow = await db.get(Workflow, schedule.workflow_id)
        if not workflow or workflow.status not in ("active", "draft"):
            schedule.next_run_at = _next_run_at(schedule.cadence, base=now)
            continue
        try:
            version = await _current_version(db, workflow)
        except NotFoundError:
            schedule.next_run_at = _next_run_at(schedule.cadence, base=now)
            continue
        await _create_run(
            db,
            workflow=workflow,
            version=version,
            trigger_type="schedule",
            trigger_event="schedule",
            payload={"event": "schedule", "title": workflow.name},
            metadata={"schedule_id": str(schedule.id)},
        )
        schedule.last_run_at = now
        schedule.next_run_at = _next_run_at(schedule.cadence, base=now)
        count += 1
    await db.flush()
    return count


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #


async def process_run_queue(db: AsyncSession, limit: int = 20) -> dict[str, int]:
    now = utcnow()
    runs = await db.scalars(
        select(WorkflowRun)
        .where(
            WorkflowRun.status == "pending",
            (WorkflowRun.next_attempt_at.is_(None))
            | (WorkflowRun.next_attempt_at <= now),
        )
        .order_by(WorkflowRun.created_at.asc())
        .limit(limit)
    )
    processed = 0
    succeeded = 0
    failed = 0
    for run in list(runs):
        await execute_run(db, run)
        processed += 1
        if run.status == "succeeded":
            succeeded += 1
        elif run.status in ("failed", "dead"):
            failed += 1
    await db.flush()
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


async def execute_run(db: AsyncSession, run: WorkflowRun) -> WorkflowRun:
    """Execute pending steps of a run in order until completion or interruption."""
    if run.status in ("succeeded", "failed", "cancelled", "dead"):
        return run

    run.status = "running"
    if not run.started_at:
        run.started_at = utcnow()
    await db.flush()

    steps = await db.scalars(
        select(WorkflowRunStep)
        .where(WorkflowRunStep.run_id == run.id)
        .order_by(WorkflowRunStep.step_index.asc())
    )
    steps = list(steps)

    source = _interp_source(
        organization_id=run.organization_id,
        payload=run.trigger_payload or {},
        context=run.context or {},
    )

    for step in steps:
        if step.status != "pending":
            continue

        input_json = step.input_json or {}
        conditions = input_json.get("conditions")
        if not workflow_schema.evaluate_conditions(
            conditions, run.trigger_payload or {}, run.context or {}
        ):
            step.status = "skipped"
            step.finished_at = utcnow()
            await db.flush()
            continue

        config = _interpolate(dict(input_json.get("config") or {}), source)
        step.status = "running"
        step.started_at = step.started_at or utcnow()
        step.attempt_count = (step.attempt_count or 0) + 1
        await db.flush()

        try:
            control, output = await _run_action(db, run, step, config)
        except Exception as exc:  # noqa: BLE001
            await _handle_step_failure(db, run, step, str(exc))
            return run

        step.output_json = output or {}

        if control == "delay":
            step.status = "succeeded"
            step.finished_at = utcnow()
            run.status = "pending"
            delay_seconds = int((output or {}).get("delay_seconds") or 60)
            run.next_attempt_at = utcnow() + timedelta(seconds=delay_seconds)
            await db.flush()
            await _audit_run(db, run, "workflows.run.delayed")
            return run

        if control == "approval":
            step.status = "waiting"
            run.status = "waiting_approval"
            await db.flush()
            await _audit_run(db, run, "workflows.run.waiting_approval")
            return run

        if control == "terminate":
            step.status = "succeeded"
            step.finished_at = utcnow()
            run.status = "succeeded"
            run.finished_at = utcnow()
            await db.flush()
            await _audit_run(db, run, "workflows.run.terminated")
            return run

        step.status = "succeeded"
        step.finished_at = utcnow()
        await db.flush()

    run.status = "succeeded"
    run.finished_at = utcnow()
    await db.flush()
    await _audit_run(db, run, "workflows.run.succeeded")
    return run


async def _handle_step_failure(
    db: AsyncSession, run: WorkflowRun, step: WorkflowRunStep, error: str
) -> None:
    step.error_message = error[:1000]
    run.attempt_count = (run.attempt_count or 0) + 1
    run.error_message = error[:1000]
    if run.attempt_count >= (run.max_attempts or 5):
        step.status = "failed"
        step.finished_at = utcnow()
        run.status = "dead"
        run.finished_at = utcnow()
        run.next_attempt_at = None
        await db.flush()
        await _audit_run(db, run, "workflows.run.dead")
    else:
        step.status = "pending"  # retry same step next attempt
        run.status = "pending"
        delay = BACKOFF_SECONDS[min(run.attempt_count - 1, len(BACKOFF_SECONDS) - 1)]
        run.next_attempt_at = utcnow() + timedelta(seconds=delay)
        await db.flush()
        await _audit_run(db, run, "workflows.run.retry")


async def _audit_run(db: AsyncSession, run: WorkflowRun, action: str) -> None:
    try:
        await write_audit_log(
            db,
            action=action,
            resource_type="workflow_run",
            resource_id=run.id,
            organization_id=run.organization_id,
            actor_id=run.created_by_id,
            description=f"{action} for run {run.id}",
            metadata={"workflow_id": str(run.workflow_id), "status": run.status},
        )
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# Action implementations (reuse existing services only)
# --------------------------------------------------------------------------- #


async def _member_emails(
    db: AsyncSession, organization_id: UUID, role_slugs: Optional[list[str]] = None
) -> list[str]:
    filters = [
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.status == "active",
    ]
    query = (
        select(User.email)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .join(Role, Role.id == OrganizationMembership.role_id)
        .where(*filters)
    )
    if role_slugs:
        query = query.where(Role.slug.in_(role_slugs))
    rows = await db.scalars(query.distinct())
    return [e for e in rows if e]


async def _run_action(
    db: AsyncSession, run: WorkflowRun, step: WorkflowRunStep, config: dict
) -> tuple[str, dict]:
    """Dispatch a single action. Returns ``(control, output)``.

    ``control`` is one of ``continue | delay | approval | terminate``.
    """
    atype = step.action_type
    org_id = run.organization_id

    if atype == "send_notification":
        created = await notification_service.notify_org_members(
            db,
            organization_id=org_id,
            event_type="workflow.notification",
            title=(config.get("title") or run.trigger_payload.get("title") or "Workflow")[:255],
            body=config.get("body"),
            link=config.get("link"),
            severity=config.get("severity") or "info",
            resource_type="workflow_run",
            resource_id=str(run.id),
            role_slugs=config.get("role_slugs"),
            metadata={"workflow_id": str(run.workflow_id)},
        )
        return "continue", {"notified": len(created)}

    if atype == "send_email":
        recipients = config.get("to")
        if isinstance(recipients, str):
            recipients = [recipients]
        if not recipients:
            recipients = await _member_emails(db, org_id, config.get("role_slugs"))
        from app.services import mailer

        sent = 0
        for email in recipients:
            result = await mailer.send_email(
                to=email,
                subject=(config.get("subject") or "ImpactFlow workflow")[:255],
                body=config.get("body") or "",
            )
            if result.get("status") in ("sent", "queued_stub"):
                sent += 1
        return "continue", {"emails_sent": sent, "recipients": len(recipients)}

    if atype == "send_slack":
        deliveries = await events_service.enqueue_webhooks(
            db,
            organization_id=org_id,
            event_type="workflow.slack",
            payload={
                "event": "workflow.slack",
                "title": config.get("title") or run.trigger_payload.get("title"),
                "body": config.get("body"),
                "organization_id": str(org_id),
            },
        )
        return "continue", {"deliveries": len(deliveries)}

    if atype == "create_task":
        project_id = config.get("project_id") or (run.context or {}).get("project_id")
        if not project_id:
            return "continue", {"skipped": "no project_id in config or context"}
        from app.models.project import Project

        project = await db.scalar(
            select(Project).where(
                Project.id == UUID(str(project_id)),
                Project.organization_id == org_id,
            )
        )
        if not project:
            raise NotFoundError("Project not found for create_task")
        task = Task(
            organization_id=org_id,
            project_id=project.id,
            title=(config.get("title") or "Workflow task")[:255],
            description=config.get("description"),
            status="todo",
            priority=config.get("priority") or "medium",
            created_by_id=run.created_by_id,
            metadata_={"workflow_run_id": str(run.id)},
        )
        db.add(task)
        await db.flush()
        return "continue", {"task_id": str(task.id)}

    if atype == "assign_user":
        task_id = config.get("task_id") or (run.context or {}).get("task_id")
        assignee_id = config.get("assignee_id") or config.get("user_id")
        if not task_id or not assignee_id:
            return "continue", {"skipped": "missing task_id or assignee_id"}
        task = await db.scalar(
            select(Task).where(
                Task.id == UUID(str(task_id)), Task.organization_id == org_id
            )
        )
        if not task:
            raise NotFoundError("Task not found for assign_user")
        task.assignee_id = UUID(str(assignee_id))
        await db.flush()
        return "continue", {"task_id": str(task.id), "assignee_id": str(assignee_id)}

    if atype in ("generate_ai_report", "generate_executive_summary"):
        from app.services import ai as ai_service

        report_type = config.get("report_type") or (
            "executive_brief" if atype == "generate_executive_summary" else "program_summary"
        )
        result = await ai_service.generate_report(
            db,
            organization_id=org_id,
            actor_id=run.created_by_id or run.organization_id,
            report_type=report_type,
            save_narrative=True,
        )
        return "continue", {
            "narrative_id": result.get("narrative_id"),
            "report_type": result.get("report_type"),
            "provider": result.get("provider"),
        }

    if atype == "update_record":
        return "continue", await _action_update_record(db, org_id, config)

    if atype == "create_audit_event":
        await write_audit_log(
            db,
            action=config.get("action") or "workflows.action.audit",
            resource_type=config.get("resource_type") or "workflow_run",
            resource_id=config.get("resource_id") or str(run.id),
            organization_id=org_id,
            actor_id=run.created_by_id,
            description=config.get("description") or "Workflow audit event",
        )
        return "continue", {"audited": True}

    if atype == "log_message":
        message = config.get("message") or config.get("body") or ""
        return "continue", {"message": message}

    if atype == "call_webhook":
        deliveries = await events_service.enqueue_webhooks(
            db,
            organization_id=org_id,
            event_type=config.get("event_type") or "workflow.webhook",
            payload={
                "event": config.get("event_type") or "workflow.webhook",
                "organization_id": str(org_id),
                "workflow_id": str(run.workflow_id),
                "data": config.get("data") or {},
                "title": run.trigger_payload.get("title"),
            },
        )
        return "continue", {"deliveries": len(deliveries)}

    if atype == "http_request":
        url = config.get("url")
        if not url:
            return "continue", {"skipped": "no url"}
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=config.get("body") or {})
            return "continue", {"status": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            return "continue", {"status": None, "error": str(exc)[:300]}

    if atype == "delay":
        seconds = config.get("delay_seconds")
        if seconds is None:
            minutes = config.get("delay_minutes")
            seconds = int(minutes) * 60 if minutes is not None else 60
        return "delay", {"delay_seconds": int(seconds)}

    if atype == "approval_request":
        assignee_id = config.get("assignee_id")
        due_hours = config.get("due_hours")
        approval = WorkflowApproval(
            organization_id=org_id,
            run_id=run.id,
            step_id=step.id,
            status="pending",
            assignee_id=UUID(str(assignee_id)) if assignee_id else None,
            due_at=utcnow() + timedelta(hours=int(due_hours)) if due_hours else None,
            metadata_={
                "title": config.get("title") or "Approval required",
                "role_slugs": config.get("role_slugs") or [],
            },
        )
        db.add(approval)
        await db.flush()
        # Notify potential approvers via the shared notification stack.
        await notification_service.notify_org_members(
            db,
            organization_id=org_id,
            event_type="workflow.approval_request",
            title=(config.get("title") or "Approval required")[:255],
            body=config.get("body"),
            link="/app/workflows/approvals",
            severity="info",
            resource_type="workflow_approval",
            resource_id=str(approval.id),
            role_slugs=config.get("role_slugs") or ["org_admin", "manager"],
            metadata={"run_id": str(run.id)},
        )
        return "approval", {"approval_id": str(approval.id)}

    if atype == "terminate_workflow":
        return "terminate", {"terminated": True}

    if atype == "branch_noop":
        return "continue", {"branch": True}

    return "continue", {"noop": f"unknown action {atype}"}


_UPDATABLE_FIELDS = {
    "task": {"status", "priority", "title", "description"},
    "project": {"status", "name", "description"},
    "grant": {"status"},
}


async def _action_update_record(
    db: AsyncSession, organization_id: UUID, config: dict
) -> dict:
    resource_type = config.get("resource_type")
    resource_id = config.get("resource_id")
    fields = config.get("fields") or {}
    if resource_type not in _UPDATABLE_FIELDS or not resource_id:
        return {"skipped": "unsupported resource_type or missing id"}

    model_map = {
        "task": Task,
    }
    if resource_type == "project":
        from app.models.project import Project

        model_map["project"] = Project
    if resource_type == "grant":
        from app.models.grant import Grant

        model_map["grant"] = Grant

    model = model_map.get(resource_type)
    if model is None:
        return {"skipped": "unsupported resource_type"}

    row = await db.scalar(
        select(model).where(
            model.id == UUID(str(resource_id)),
            model.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError(f"{resource_type} not found for update_record")

    allowed = _UPDATABLE_FIELDS[resource_type]
    applied: dict[str, Any] = {}
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(row, key, value)
            applied[key] = value
    await db.flush()
    return {"updated": resource_type, "fields": applied}


# --------------------------------------------------------------------------- #
# Runs (read) & cancellation
# --------------------------------------------------------------------------- #


async def list_runs(
    db: AsyncSession,
    organization_id: UUID,
    *,
    workflow_id: Optional[UUID] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WorkflowRun], int]:
    filters = [WorkflowRun.organization_id == organization_id]
    if workflow_id:
        filters.append(WorkflowRun.workflow_id == workflow_id)
    if status:
        filters.append(WorkflowRun.status == status)
    total = await db.scalar(select(func.count()).select_from(WorkflowRun).where(*filters)) or 0
    rows = await db.scalars(
        select(WorkflowRun)
        .where(*filters)
        .order_by(WorkflowRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def get_run(db: AsyncSession, organization_id: UUID, run_id: UUID) -> WorkflowRun:
    row = await db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id, WorkflowRun.organization_id == organization_id
        )
    )
    if not row:
        raise NotFoundError("Workflow run not found")
    return row


async def list_run_steps(
    db: AsyncSession, organization_id: UUID, run_id: UUID
) -> list[WorkflowRunStep]:
    rows = await db.scalars(
        select(WorkflowRunStep)
        .where(
            WorkflowRunStep.organization_id == organization_id,
            WorkflowRunStep.run_id == run_id,
        )
        .order_by(WorkflowRunStep.step_index.asc())
    )
    return list(rows)


async def cancel_run(
    db: AsyncSession, run: WorkflowRun, *, actor_id: UUID
) -> WorkflowRun:
    if run.status in ("succeeded", "failed", "dead", "cancelled"):
        raise ConflictError("Run already finished")
    run.status = "cancelled"
    run.finished_at = utcnow()
    run.next_attempt_at = None
    await db.flush()
    await _audit_run(db, run, "workflows.run.cancelled")
    return run


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #


async def list_approvals(
    db: AsyncSession,
    organization_id: UUID,
    *,
    status: Optional[str] = "pending",
    assignee_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WorkflowApproval], int]:
    filters = [WorkflowApproval.organization_id == organization_id]
    if status:
        filters.append(WorkflowApproval.status == status)
    if assignee_id:
        filters.append(WorkflowApproval.assignee_id == assignee_id)
    total = await db.scalar(
        select(func.count()).select_from(WorkflowApproval).where(*filters)
    ) or 0
    rows = await db.scalars(
        select(WorkflowApproval)
        .where(*filters)
        .order_by(WorkflowApproval.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def get_approval(
    db: AsyncSession, organization_id: UUID, approval_id: UUID
) -> WorkflowApproval:
    row = await db.scalar(
        select(WorkflowApproval).where(
            WorkflowApproval.id == approval_id,
            WorkflowApproval.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Approval not found")
    return row


async def decide_approval(
    db: AsyncSession,
    organization_id: UUID,
    approval_id: UUID,
    *,
    decision: str,
    comments: Optional[str] = None,
    actor_id: UUID,
) -> WorkflowApproval:
    if decision not in ("approved", "rejected", "returned"):
        raise AppError(
            "Invalid decision", code="VALIDATION_ERROR", status_code=422
        )
    approval = await get_approval(db, organization_id, approval_id)
    if approval.status != "pending":
        raise ConflictError("Approval already decided")

    approval.status = decision
    approval.comments = comments
    approval.decided_at = utcnow()
    approval.decided_by_id = actor_id
    await db.flush()

    run = await db.get(WorkflowRun, approval.run_id)
    step = await db.get(WorkflowRunStep, approval.step_id)

    if decision == "approved":
        if step:
            step.status = "succeeded"
            step.finished_at = utcnow()
        if run:
            run.status = "pending"
            run.next_attempt_at = utcnow()
            await db.flush()
            await execute_run(db, run)
    else:
        # reject/return -> pause the run as failed (returned kept distinct via approval)
        if step:
            step.status = "failed"
            step.finished_at = utcnow()
            step.error_message = f"Approval {decision}"
        if run:
            run.status = "failed"
            run.finished_at = utcnow()
            run.next_attempt_at = None
            run.error_message = f"Approval {decision}"
    await db.flush()

    await write_audit_log(
        db,
        action=f"workflows.approval.{decision}",
        resource_type="workflow_approval",
        resource_id=approval.id,
        organization_id=organization_id,
        actor_id=actor_id,
        description=f"Approval {decision} for run {approval.run_id}",
    )
    return approval


# --------------------------------------------------------------------------- #
# Metrics & dashboard counts
# --------------------------------------------------------------------------- #


async def workflow_metrics(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    status_result = await db.execute(
        select(Workflow.status, func.count())
        .where(Workflow.organization_id == organization_id)
        .group_by(Workflow.status)
    )
    workflow_status_counts = {row[0]: row[1] for row in status_result.all()}

    run_status_result = await db.execute(
        select(WorkflowRun.status, func.count())
        .where(WorkflowRun.organization_id == organization_id)
        .group_by(WorkflowRun.status)
    )
    run_status_counts = {row[0]: row[1] for row in run_status_result.all()}

    since = utcnow() - timedelta(days=7)
    recent_total = await db.scalar(
        select(func.count())
        .select_from(WorkflowRun)
        .where(
            WorkflowRun.organization_id == organization_id,
            WorkflowRun.created_at >= since,
        )
    ) or 0
    recent_success = await db.scalar(
        select(func.count())
        .select_from(WorkflowRun)
        .where(
            WorkflowRun.organization_id == organization_id,
            WorkflowRun.created_at >= since,
            WorkflowRun.status == "succeeded",
        )
    ) or 0
    recent_failed = await db.scalar(
        select(func.count())
        .select_from(WorkflowRun)
        .where(
            WorkflowRun.organization_id == organization_id,
            WorkflowRun.created_at >= since,
            WorkflowRun.status.in_(["failed", "dead"]),
        )
    ) or 0
    queue_depth = run_status_counts.get("pending", 0)

    return {
        "workflow_status_counts": workflow_status_counts,
        "run_status_counts": run_status_counts,
        "runs_last_7d": recent_total,
        "success_rate_7d": round(recent_success / recent_total, 3) if recent_total else 0.0,
        "failure_rate_7d": round(recent_failed / recent_total, 3) if recent_total else 0.0,
        "queue_depth": queue_depth,
        "pending_approvals": await db.scalar(
            select(func.count())
            .select_from(WorkflowApproval)
            .where(
                WorkflowApproval.organization_id == organization_id,
                WorkflowApproval.status == "pending",
            )
        )
        or 0,
    }


async def phase14_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    workflows = await db.scalar(
        select(func.count())
        .select_from(Workflow)
        .where(Workflow.organization_id == organization_id)
    )
    active = await db.scalar(
        select(func.count())
        .select_from(Workflow)
        .where(
            Workflow.organization_id == organization_id,
            Workflow.status == "active",
        )
    )
    runs = await db.scalar(
        select(func.count())
        .select_from(WorkflowRun)
        .where(WorkflowRun.organization_id == organization_id)
    )
    return {
        "workflows_count": workflows or 0,
        "active_workflows_count": active or 0,
        "workflow_runs_count": runs or 0,
    }
