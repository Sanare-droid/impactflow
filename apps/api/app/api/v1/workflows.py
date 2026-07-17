"""Workflow automation API — thin HTTP layer over app.services.workflows."""

from __future__ import annotations

from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import MessageResponse, ORMModel, PaginatedResponse, PaginationMeta
from app.services import workflow_schema
from app.services import workflows as workflow_service

router = APIRouter(tags=["Workflows"])

READ_PERMS = ("workflows:read", "workflows:manage")
MANAGE_PERMS = ("workflows:manage",)
APPROVE_PERMS = ("workflows:approve", "workflows:manage")


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #


class WorkflowCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default="draft", max_length=32)
    is_template: bool = False
    definition: Optional[dict[str, Any]] = None
    changelog: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class WorkflowUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=128)
    status: Optional[str] = Field(default=None, max_length=32)
    is_template: Optional[bool] = None
    definition: Optional[dict[str, Any]] = None
    changelog: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class CloneRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class ImportDefinitionRequest(BaseModel):
    definition: dict[str, Any]
    changelog: Optional[str] = None


class ManualRunRequest(BaseModel):
    inputs: Optional[dict[str, Any]] = None


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|returned)$")
    comments: Optional[str] = None


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cadence: str = Field(default="daily", max_length=32)
    cron_expr: Optional[str] = Field(default=None, max_length=128)
    timezone: str = Field(default="UTC", max_length=64)
    enabled: bool = True
    metadata: Optional[dict[str, Any]] = None


class ScheduleUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cadence: Optional[str] = Field(default=None, max_length=32)
    cron_expr: Optional[str] = Field(default=None, max_length=128)
    timezone: Optional[str] = Field(default=None, max_length=64)
    enabled: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class WorkflowOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    current_version: int
    is_template: bool
    cloned_from_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class WorkflowVersionOut(ORMModel):
    id: UUID
    workflow_id: UUID
    version: int
    title: str
    changelog: Optional[str] = None
    published_at: Optional[Any] = None
    created_by_id: Optional[UUID] = None
    created_at: Any


class WorkflowRunOut(ORMModel):
    id: UUID
    organization_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    status: str
    trigger_type: str
    trigger_event: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int
    max_attempts: int
    next_attempt_at: Optional[Any] = None
    started_at: Optional[Any] = None
    finished_at: Optional[Any] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class WorkflowRunStepOut(ORMModel):
    id: UUID
    run_id: UUID
    step_index: int
    action_id: str
    action_type: str
    status: str
    input_json: dict
    output_json: dict
    error_message: Optional[str] = None
    attempt_count: int
    started_at: Optional[Any] = None
    finished_at: Optional[Any] = None


class WorkflowApprovalOut(ORMModel):
    id: UUID
    organization_id: UUID
    run_id: UUID
    step_id: UUID
    status: str
    assignee_id: Optional[UUID] = None
    comments: Optional[str] = None
    decided_at: Optional[Any] = None
    decided_by_id: Optional[UUID] = None
    due_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


class WorkflowScheduleOut(ORMModel):
    id: UUID
    organization_id: UUID
    workflow_id: UUID
    cadence: str
    cron_expr: Optional[str] = None
    timezone: str
    enabled: bool
    next_run_at: Optional[Any] = None
    last_run_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Catalogs & templates (static paths first so they don't shadow /{workflow_id})
# --------------------------------------------------------------------------- #


@router.get("/workflows/triggers")
async def list_triggers(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
) -> dict[str, Any]:
    return {"triggers": workflow_schema.list_trigger_types()}


@router.get("/workflows/actions")
async def list_actions(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
) -> dict[str, Any]:
    return {"actions": workflow_schema.list_action_types()}


@router.get("/workflows/operators")
async def list_operators(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
) -> dict[str, Any]:
    return {"operators": workflow_schema.list_condition_operators()}


@router.get("/workflows/templates")
async def list_templates(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return {"templates": await workflow_service.list_templates(db, org_id)}


@router.post("/workflows/templates/{template_code}/clone", response_model=WorkflowOut, status_code=201)
async def clone_template(
    template_code: str,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.clone_template(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        template_code=template_code,
    )
    return WorkflowOut.model_validate(workflow)


@router.get("/workflows/metrics")
async def workflow_metrics(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    return await workflow_service.workflow_metrics(db, org_id)


# --------------------------------------------------------------------------- #
# Workflow CRUD
# --------------------------------------------------------------------------- #


@router.get("/workflows", response_model=PaginatedResponse[WorkflowOut])
async def list_workflows(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    is_template: Optional[bool] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[WorkflowOut]:
    org_id = _require_org(ctx)
    items, total = await workflow_service.list_workflows(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        is_template=is_template,
        search=search,
    )
    return PaginatedResponse(
        items=[WorkflowOut.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/workflows", response_model=WorkflowOut, status_code=201)
async def create_workflow(
    body: WorkflowCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    workflow = await workflow_service.create_workflow(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return WorkflowOut.model_validate(workflow)


async def _get_workflow_detail(db: AsyncSession, org_id: UUID, workflow) -> dict[str, Any]:
    definition = await workflow_service.export_definition(db, workflow)
    payload = WorkflowOut.model_validate(workflow).model_dump()
    payload["definition"] = definition.get("definition")
    payload["metadata"] = workflow.metadata_ or {}
    return payload


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    return await _get_workflow_detail(db, org_id, workflow)


@router.patch("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: UUID,
    body: WorkflowUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    workflow = await workflow_service.update_workflow(
        db,
        workflow,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return await _get_workflow_detail(db, org_id, workflow)


@router.post("/workflows/{workflow_id}/clone", response_model=WorkflowOut, status_code=201)
async def clone_workflow(
    workflow_id: UUID,
    body: CloneRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    clone = await workflow_service.clone_workflow(
        db, workflow, actor_id=ctx.user.id, actor_email=ctx.user.email, name=body.name
    )
    return WorkflowOut.model_validate(clone)


@router.post("/workflows/{workflow_id}/archive", response_model=WorkflowOut)
async def archive_workflow(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    workflow = await workflow_service.archive_workflow(
        db, workflow, actor_id=ctx.user.id, actor_email=ctx.user.email
    )
    return WorkflowOut.model_validate(workflow)


@router.post("/workflows/{workflow_id}/enable", response_model=WorkflowOut)
async def enable_workflow(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    workflow = await workflow_service.enable_workflow(
        db, workflow, actor_id=ctx.user.id, actor_email=ctx.user.email
    )
    return WorkflowOut.model_validate(workflow)


@router.post("/workflows/{workflow_id}/disable", response_model=WorkflowOut)
async def disable_workflow(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    workflow = await workflow_service.disable_workflow(
        db, workflow, actor_id=ctx.user.id, actor_email=ctx.user.email
    )
    return WorkflowOut.model_validate(workflow)


@router.post("/workflows/{workflow_id}/activate", response_model=WorkflowOut)
async def activate_workflow(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    workflow = await workflow_service.activate_workflow(
        db, workflow, actor_id=ctx.user.id, actor_email=ctx.user.email
    )
    return WorkflowOut.model_validate(workflow)


# --------------------------------------------------------------------------- #
# Versions & import/export
# --------------------------------------------------------------------------- #


@router.get("/workflows/{workflow_id}/versions", response_model=list[WorkflowVersionOut])
async def list_versions(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkflowVersionOut]:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    versions = await workflow_service.list_versions(db, workflow)
    return [WorkflowVersionOut.model_validate(v) for v in versions]


@router.get("/workflows/{workflow_id}/versions/{version}")
async def get_version(
    workflow_id: UUID,
    version: int,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    row = await workflow_service.get_version(db, org_id, workflow_id, version)
    payload = WorkflowVersionOut.model_validate(row).model_dump()
    payload["definition"] = row.definition_
    return payload


@router.get("/workflows/{workflow_id}/export-definition")
async def export_definition(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    return await workflow_service.export_definition(db, workflow)


@router.post("/workflows/{workflow_id}/export-definition")
async def export_definition_post(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    return await workflow_service.export_definition(db, workflow)


@router.post("/workflows/{workflow_id}/import-definition", response_model=WorkflowVersionOut, status_code=201)
async def import_definition(
    workflow_id: UUID,
    body: ImportDefinitionRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowVersionOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    version = await workflow_service.import_definition(
        db, workflow, definition=body.definition, actor_id=ctx.user.id, changelog=body.changelog
    )
    return WorkflowVersionOut.model_validate(version)


# --------------------------------------------------------------------------- #
# Manual run
# --------------------------------------------------------------------------- #


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunOut, status_code=201)
async def run_workflow(
    workflow_id: UUID,
    body: ManualRunRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRunOut:
    org_id = _require_org(ctx)
    from app.services import enterprise as ent

    await ent.require_feature(db, org_id, "workflows")
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    run = await workflow_service.enqueue_manual_run(
        db, workflow, actor_id=ctx.user.id, inputs=body.inputs
    )
    return WorkflowRunOut.model_validate(run)


# --------------------------------------------------------------------------- #
# Schedules
# --------------------------------------------------------------------------- #


@router.get("/workflows/{workflow_id}/schedules", response_model=list[WorkflowScheduleOut])
async def list_schedules(
    workflow_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkflowScheduleOut]:
    org_id = _require_org(ctx)
    await workflow_service.get_workflow(db, org_id, workflow_id)
    rows = await workflow_service.list_schedules(db, org_id, workflow_id)
    return [WorkflowScheduleOut.model_validate(r) for r in rows]


@router.post("/workflows/{workflow_id}/schedules", response_model=WorkflowScheduleOut, status_code=201)
async def create_schedule(
    workflow_id: UUID,
    body: ScheduleCreateRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowScheduleOut:
    org_id = _require_org(ctx)
    workflow = await workflow_service.get_workflow(db, org_id, workflow_id)
    row = await workflow_service.create_schedule(
        db, workflow, data=body.model_dump(exclude_unset=True), actor_id=ctx.user.id
    )
    return WorkflowScheduleOut.model_validate(row)


@router.patch("/workflows/{workflow_id}/schedules/{schedule_id}", response_model=WorkflowScheduleOut)
async def update_schedule(
    workflow_id: UUID,
    schedule_id: UUID,
    body: ScheduleUpdateRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowScheduleOut:
    org_id = _require_org(ctx)
    schedule = await workflow_service.get_schedule(db, org_id, schedule_id)
    if schedule.workflow_id != workflow_id:
        raise NotFoundError("Schedule not found")
    row = await workflow_service.update_schedule(
        db, schedule, data=body.model_dump(exclude_unset=True), actor_id=ctx.user.id
    )
    return WorkflowScheduleOut.model_validate(row)


@router.delete("/workflows/{workflow_id}/schedules/{schedule_id}", response_model=MessageResponse)
async def delete_schedule(
    workflow_id: UUID,
    schedule_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    schedule = await workflow_service.get_schedule(db, org_id, schedule_id)
    if schedule.workflow_id != workflow_id:
        raise NotFoundError("Schedule not found")
    await workflow_service.delete_schedule(db, schedule, actor_id=ctx.user.id)
    return MessageResponse(message="Schedule deleted")


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #


@router.get("/workflow-runs", response_model=PaginatedResponse[WorkflowRunOut])
async def list_runs(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workflow_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> PaginatedResponse[WorkflowRunOut]:
    org_id = _require_org(ctx)
    items, total = await workflow_service.list_runs(
        db, org_id, workflow_id=workflow_id, status=status, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[WorkflowRunOut.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.get("/workflow-runs/{run_id}")
async def get_run(
    run_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    org_id = _require_org(ctx)
    run = await workflow_service.get_run(db, org_id, run_id)
    steps = await workflow_service.list_run_steps(db, org_id, run_id)
    payload = WorkflowRunOut.model_validate(run).model_dump()
    payload["steps"] = [WorkflowRunStepOut.model_validate(s).model_dump() for s in steps]
    payload["trigger_payload"] = run.trigger_payload or {}
    payload["context"] = run.context or {}
    return payload


@router.post("/workflow-runs/{run_id}/cancel", response_model=WorkflowRunOut)
async def cancel_run(
    run_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRunOut:
    org_id = _require_org(ctx)
    run = await workflow_service.get_run(db, org_id, run_id)
    run = await workflow_service.cancel_run(db, run, actor_id=ctx.user.id)
    return WorkflowRunOut.model_validate(run)


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #


@router.get("/workflow-approvals", response_model=PaginatedResponse[WorkflowApprovalOut])
async def list_approvals(
    ctx: Annotated[RequestContext, Depends(require_permissions("workflows:read", "workflows:approve", "workflows:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = "pending",
    mine: bool = False,
) -> PaginatedResponse[WorkflowApprovalOut]:
    org_id = _require_org(ctx)
    items, total = await workflow_service.list_approvals(
        db,
        org_id,
        status=status,
        assignee_id=ctx.user.id if mine else None,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[WorkflowApprovalOut.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/workflow-approvals/{approval_id}/decide", response_model=WorkflowApprovalOut)
async def decide_approval(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions(*APPROVE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowApprovalOut:
    org_id = _require_org(ctx)
    approval = await workflow_service.decide_approval(
        db,
        org_id,
        approval_id,
        decision=body.decision,
        comments=body.comments,
        actor_id=ctx.user.id,
    )
    return WorkflowApprovalOut.model_validate(approval)
