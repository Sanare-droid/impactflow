from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    ActivityCreateRequest,
    ActivityResponse,
    ActivityUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    ProgramCreateRequest,
    ProgramResponse,
    ProgramUpdateRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
    WorkPlanCreateRequest,
    WorkPlanResponse,
    WorkPlanUpdateRequest,
)
from app.services import programs as program_service

router = APIRouter(tags=["Programs & Projects"])


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


# -------- Programs --------


@router.get("/programs", response_model=PaginatedResponse[ProgramResponse])
async def list_programs(
    ctx: Annotated[RequestContext, Depends(require_permissions("programs:read", "programs:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[ProgramResponse]:
    org_id = _require_org(ctx)
    items, total = await program_service.list_programs(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[ProgramResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    body: ProgramCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("programs:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    program = await program_service.create_program(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        name=body.name,
        code=body.code,
        description=body.description,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
        manager_id=body.manager_id,
        goal=body.goal,
        tags=body.tags,
        ip_address=ip,
        user_agent=ua,
    )
    return ProgramResponse.model_validate(program)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("programs:read", "programs:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramResponse:
    org_id = _require_org(ctx)
    program = await program_service.get_program(db, org_id, program_id)
    return ProgramResponse.model_validate(program)


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    body: ProgramUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("programs:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    program = await program_service.get_program(db, org_id, program_id)
    updated = await program_service.update_program(
        db,
        program,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ProgramResponse.model_validate(updated)


@router.delete("/programs/{program_id}", response_model=MessageResponse)
async def delete_program(
    program_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("programs:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    program = await program_service.get_program(db, org_id, program_id)
    await program_service.delete_program(
        db,
        program,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Program deleted")


# -------- Projects --------


@router.get("/projects", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    ctx: Annotated[RequestContext, Depends(require_permissions("projects:read", "projects:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    program_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[ProjectResponse]:
    org_id = _require_org(ctx)
    items, total = await program_service.list_projects(
        db,
        org_id,
        page=page,
        page_size=page_size,
        program_id=program_id,
        status=status,
        search=search,
    )
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("projects:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    project = await program_service.create_project(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        program_id=body.program_id,
        name=body.name,
        code=body.code,
        description=body.description,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
        country_code=body.country_code,
        location=body.location,
        manager_id=body.manager_id,
        priority=body.priority,
        tags=body.tags,
        ip_address=ip,
        user_agent=ua,
    )
    return ProjectResponse.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("projects:read", "projects:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    org_id = _require_org(ctx)
    project = await program_service.get_project(db, org_id, project_id)
    return ProjectResponse.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("projects:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    project = await program_service.get_project(db, org_id, project_id)
    updated = await program_service.update_project(
        db,
        project,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ProjectResponse.model_validate(updated)


@router.delete("/projects/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("projects:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    project = await program_service.get_project(db, org_id, project_id)
    await program_service.delete_project(
        db,
        project,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Project deleted")


# -------- Activities --------


@router.get("/activities", response_model=PaginatedResponse[ActivityResponse])
async def list_activities(
    ctx: Annotated[RequestContext, Depends(require_permissions("activities:read", "activities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[ActivityResponse]:
    org_id = _require_org(ctx)
    items, total = await program_service.list_activities(
        db, org_id, project_id=project_id, page=page, page_size=page_size, status=status
    )
    return PaginatedResponse(
        items=[ActivityResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/activities", response_model=ActivityResponse, status_code=201)
async def create_activity(
    body: ActivityCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("activities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ActivityResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    activity = await program_service.create_activity(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        project_id=body.project_id,
        name=body.name,
        code=body.code,
        description=body.description,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
        sort_order=body.sort_order,
        owner_id=body.owner_id,
        location=body.location,
        ip_address=ip,
        user_agent=ua,
    )
    return ActivityResponse.model_validate(activity)


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: UUID,
    body: ActivityUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("activities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ActivityResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    activity = await program_service.get_activity(db, org_id, activity_id)
    updated = await program_service.update_activity(
        db,
        activity,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ActivityResponse.model_validate(updated)


@router.delete("/activities/{activity_id}", response_model=MessageResponse)
async def delete_activity(
    activity_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("activities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    activity = await program_service.get_activity(db, org_id, activity_id)
    await program_service.delete_activity(
        db,
        activity,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Activity deleted")


# -------- Work plans --------


@router.get("/work-plans", response_model=PaginatedResponse[WorkPlanResponse])
async def list_work_plans(
    ctx: Annotated[RequestContext, Depends(require_permissions("work_plans:read", "work_plans:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[WorkPlanResponse]:
    org_id = _require_org(ctx)
    items, total = await program_service.list_work_plans(
        db, org_id, project_id=project_id, page=page, page_size=page_size, status=status
    )
    return PaginatedResponse(
        items=[WorkPlanResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/work-plans", response_model=WorkPlanResponse, status_code=201)
async def create_work_plan(
    body: WorkPlanCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("work_plans:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkPlanResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    plan = await program_service.create_work_plan(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        project_id=body.project_id,
        name=body.name,
        description=body.description,
        status=body.status,
        period_start=body.period_start,
        period_end=body.period_end,
        fiscal_year=body.fiscal_year,
        period_label=body.period_label,
        ip_address=ip,
        user_agent=ua,
    )
    return WorkPlanResponse.model_validate(plan)


@router.patch("/work-plans/{work_plan_id}", response_model=WorkPlanResponse)
async def update_work_plan(
    work_plan_id: UUID,
    body: WorkPlanUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("work_plans:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkPlanResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    plan = await program_service.get_work_plan(db, org_id, work_plan_id)
    updated = await program_service.update_work_plan(
        db,
        plan,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return WorkPlanResponse.model_validate(updated)


@router.delete("/work-plans/{work_plan_id}", response_model=MessageResponse)
async def delete_work_plan(
    work_plan_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("work_plans:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    plan = await program_service.get_work_plan(db, org_id, work_plan_id)
    await program_service.delete_work_plan(
        db,
        plan,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Work plan deleted")


# -------- Tasks --------


@router.get("/tasks", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    ctx: Annotated[RequestContext, Depends(require_permissions("tasks:read", "tasks:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    project_id: Optional[UUID] = None,
    activity_id: Optional[UUID] = None,
    work_plan_id: Optional[UUID] = None,
    status: Optional[str] = None,
    assignee_id: Optional[UUID] = None,
) -> PaginatedResponse[TaskResponse]:
    org_id = _require_org(ctx)
    items, total = await program_service.list_tasks(
        db,
        org_id,
        page=page,
        page_size=page_size,
        project_id=project_id,
        activity_id=activity_id,
        work_plan_id=work_plan_id,
        status=status,
        assignee_id=assignee_id,
    )
    return PaginatedResponse(
        items=[TaskResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("tasks:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    task = await program_service.create_task(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        activity_id=body.activity_id,
        work_plan_id=body.work_plan_id,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
        ip_address=ip,
        user_agent=ua,
    )
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("tasks:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    task = await program_service.get_task(db, org_id, task_id)
    updated = await program_service.update_task(
        db,
        task,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return TaskResponse.model_validate(updated)


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("tasks:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    task = await program_service.get_task(db, org_id, task_id)
    await program_service.delete_task(
        db,
        task,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Task deleted")
