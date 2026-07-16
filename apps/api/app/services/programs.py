from __future__ import annotations

import re
import secrets
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import utcnow
from app.models.activity import Activity
from app.models.program import Program
from app.models.project import Project
from app.models.task import Task
from app.models.work_plan import WorkPlan
from app.services.audit import write_audit_log


def make_code(value: str, *, prefix: str = "") -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
    slug = re.sub(r"-+", "-", slug)[:40] or secrets.token_hex(3).upper()
    return f"{prefix}{slug}" if prefix else slug


async def _ensure_unique_code(
    db: AsyncSession,
    *,
    model,
    organization_id: UUID,
    code: str,
) -> str:
    base = code
    attempt = code
    n = 1
    while True:
        existing = await db.scalar(
            select(model.id).where(
                model.organization_id == organization_id,
                model.code == attempt,
            )
        )
        if not existing:
            return attempt
        n += 1
        attempt = f"{base}-{n}"


async def get_program(db: AsyncSession, organization_id: UUID, program_id: UUID) -> Program:
    program = await db.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.organization_id == organization_id,
        )
    )
    if not program:
        raise NotFoundError("Program not found")
    return program


async def get_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> Project:
    project = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
        )
    )
    if not project:
        raise NotFoundError("Project not found")
    return project


async def list_programs(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Program], int]:
    filters = [Program.organization_id == organization_id]
    if status:
        filters.append(Program.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Program.name.ilike(like)) | (Program.code.ilike(like)))

    total = await db.scalar(select(func.count()).select_from(Program).where(*filters)) or 0
    result = await db.execute(
        select(Program)
        .where(*filters)
        .order_by(Program.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_program(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    name: str,
    code: Optional[str],
    description: Optional[str],
    status: str,
    start_date: Optional[date],
    end_date: Optional[date],
    manager_id: Optional[UUID],
    goal: Optional[str],
    tags: Optional[list],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Program:
    code_value = await _ensure_unique_code(
        db,
        model=Program,
        organization_id=organization_id,
        code=make_code(code or name),
    )
    program = Program(
        organization_id=organization_id,
        name=name.strip(),
        code=code_value,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        manager_id=manager_id,
        goal=goal,
        tags=tags or [],
        created_by_id=actor_id,
    )
    db.add(program)
    await db.flush()
    await write_audit_log(
        db,
        action="programs.create",
        resource_type="program",
        resource_id=program.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created program {program.code}",
        changes={"name": program.name, "code": program.code, "status": program.status},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return program


async def update_program(
    db: AsyncSession,
    program: Program,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Program:
    if "code" in data and data["code"]:
        new_code = make_code(data["code"])
        if new_code != program.code:
            data["code"] = await _ensure_unique_code(
                db,
                model=Program,
                organization_id=program.organization_id,
                code=new_code,
            )
    for key, value in data.items():
        setattr(program, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="programs.update",
        resource_type="program",
        resource_id=program.id,
        organization_id=program.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated program {program.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return program


async def delete_program(
    db: AsyncSession,
    program: Program,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="programs.delete",
        resource_type="program",
        resource_id=program.id,
        organization_id=program.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted program {program.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(program)
    await db.flush()


async def list_projects(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    program_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Project], int]:
    filters = [Project.organization_id == organization_id]
    if program_id:
        filters.append(Project.program_id == program_id)
    if status:
        filters.append(Project.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Project.name.ilike(like)) | (Project.code.ilike(like)))

    total = await db.scalar(select(func.count()).select_from(Project).where(*filters)) or 0
    result = await db.execute(
        select(Project)
        .where(*filters)
        .order_by(Project.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_project(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    program_id: UUID,
    name: str,
    code: Optional[str],
    description: Optional[str],
    status: str,
    start_date: Optional[date],
    end_date: Optional[date],
    country_code: Optional[str],
    location: Optional[str],
    manager_id: Optional[UUID],
    priority: str,
    tags: Optional[list],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Project:
    await get_program(db, organization_id, program_id)
    code_value = await _ensure_unique_code(
        db,
        model=Project,
        organization_id=organization_id,
        code=make_code(code or name),
    )
    project = Project(
        organization_id=organization_id,
        program_id=program_id,
        name=name.strip(),
        code=code_value,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        country_code=country_code.upper() if country_code else None,
        location=location,
        manager_id=manager_id,
        priority=priority,
        tags=tags or [],
        created_by_id=actor_id,
    )
    db.add(project)
    await db.flush()
    await write_audit_log(
        db,
        action="projects.create",
        resource_type="project",
        resource_id=project.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created project {project.code}",
        changes={"name": project.name, "program_id": str(program_id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return project


async def update_project(
    db: AsyncSession,
    project: Project,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Project:
    if "program_id" in data and data["program_id"]:
        await get_program(db, project.organization_id, data["program_id"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"])
        if new_code != project.code:
            data["code"] = await _ensure_unique_code(
                db,
                model=Project,
                organization_id=project.organization_id,
                code=new_code,
            )
    if "country_code" in data and data["country_code"]:
        data["country_code"] = data["country_code"].upper()
    for key, value in data.items():
        setattr(project, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="projects.update",
        resource_type="project",
        resource_id=project.id,
        organization_id=project.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated project {project.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return project


async def delete_project(
    db: AsyncSession,
    project: Project,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="projects.delete",
        resource_type="project",
        resource_id=project.id,
        organization_id=project.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted project {project.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(project)
    await db.flush()


async def list_activities(
    db: AsyncSession,
    organization_id: UUID,
    *,
    project_id: UUID,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> tuple[list[Activity], int]:
    await get_project(db, organization_id, project_id)
    filters = [
        Activity.organization_id == organization_id,
        Activity.project_id == project_id,
    ]
    if status:
        filters.append(Activity.status == status)
    total = await db.scalar(select(func.count()).select_from(Activity).where(*filters)) or 0
    result = await db.execute(
        select(Activity)
        .where(*filters)
        .order_by(Activity.sort_order.asc(), Activity.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_activity(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    project_id: UUID,
    name: str,
    code: Optional[str],
    description: Optional[str],
    status: str,
    start_date: Optional[date],
    end_date: Optional[date],
    sort_order: int,
    owner_id: Optional[UUID],
    location: Optional[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Activity:
    await get_project(db, organization_id, project_id)
    activity = Activity(
        organization_id=organization_id,
        project_id=project_id,
        name=name.strip(),
        code=make_code(code) if code else None,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        sort_order=sort_order,
        owner_id=owner_id,
        location=location,
        created_by_id=actor_id,
    )
    db.add(activity)
    await db.flush()
    await write_audit_log(
        db,
        action="activities.create",
        resource_type="activity",
        resource_id=activity.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created activity {activity.name}",
        changes={"project_id": str(project_id), "name": activity.name},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return activity


async def get_activity(db: AsyncSession, organization_id: UUID, activity_id: UUID) -> Activity:
    activity = await db.scalar(
        select(Activity).where(
            Activity.id == activity_id,
            Activity.organization_id == organization_id,
        )
    )
    if not activity:
        raise NotFoundError("Activity not found")
    return activity


async def update_activity(
    db: AsyncSession,
    activity: Activity,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Activity:
    if "code" in data and data["code"]:
        data["code"] = make_code(data["code"])
    for key, value in data.items():
        setattr(activity, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="activities.update",
        resource_type="activity",
        resource_id=activity.id,
        organization_id=activity.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated activity {activity.name}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return activity


async def delete_activity(
    db: AsyncSession,
    activity: Activity,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="activities.delete",
        resource_type="activity",
        resource_id=activity.id,
        organization_id=activity.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted activity {activity.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(activity)
    await db.flush()


async def list_work_plans(
    db: AsyncSession,
    organization_id: UUID,
    *,
    project_id: UUID,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> tuple[list[WorkPlan], int]:
    await get_project(db, organization_id, project_id)
    filters = [
        WorkPlan.organization_id == organization_id,
        WorkPlan.project_id == project_id,
    ]
    if status:
        filters.append(WorkPlan.status == status)
    total = await db.scalar(select(func.count()).select_from(WorkPlan).where(*filters)) or 0
    result = await db.execute(
        select(WorkPlan)
        .where(*filters)
        .order_by(WorkPlan.period_start.desc().nullslast(), WorkPlan.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_work_plan(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    project_id: UUID,
    name: str,
    description: Optional[str],
    status: str,
    period_start: Optional[date],
    period_end: Optional[date],
    fiscal_year: Optional[int],
    period_label: Optional[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> WorkPlan:
    await get_project(db, organization_id, project_id)
    plan = WorkPlan(
        organization_id=organization_id,
        project_id=project_id,
        name=name.strip(),
        description=description,
        status=status,
        period_start=period_start,
        period_end=period_end,
        fiscal_year=fiscal_year,
        period_label=period_label,
        created_by_id=actor_id,
    )
    db.add(plan)
    await db.flush()
    await write_audit_log(
        db,
        action="work_plans.create",
        resource_type="work_plan",
        resource_id=plan.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created work plan {plan.name}",
        changes={"project_id": str(project_id), "name": plan.name},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return plan


async def get_work_plan(db: AsyncSession, organization_id: UUID, work_plan_id: UUID) -> WorkPlan:
    plan = await db.scalar(
        select(WorkPlan).where(
            WorkPlan.id == work_plan_id,
            WorkPlan.organization_id == organization_id,
        )
    )
    if not plan:
        raise NotFoundError("Work plan not found")
    return plan


async def update_work_plan(
    db: AsyncSession,
    plan: WorkPlan,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> WorkPlan:
    for key, value in data.items():
        setattr(plan, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="work_plans.update",
        resource_type="work_plan",
        resource_id=plan.id,
        organization_id=plan.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated work plan {plan.name}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return plan


async def delete_work_plan(
    db: AsyncSession,
    plan: WorkPlan,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="work_plans.delete",
        resource_type="work_plan",
        resource_id=plan.id,
        organization_id=plan.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted work plan {plan.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(plan)
    await db.flush()


async def list_tasks(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    project_id: Optional[UUID] = None,
    activity_id: Optional[UUID] = None,
    work_plan_id: Optional[UUID] = None,
    status: Optional[str] = None,
    assignee_id: Optional[UUID] = None,
    updated_after: Optional[datetime] = None,
) -> tuple[list[Task], int]:
    filters = [Task.organization_id == organization_id]
    if project_id:
        filters.append(Task.project_id == project_id)
    if activity_id:
        filters.append(Task.activity_id == activity_id)
    if work_plan_id:
        filters.append(Task.work_plan_id == work_plan_id)
    if status:
        filters.append(Task.status == status)
    if assignee_id:
        filters.append(Task.assignee_id == assignee_id)
    if updated_after:
        filters.append(Task.updated_at >= updated_after)

    total = await db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0
    result = await db.execute(
        select(Task)
        .where(*filters)
        .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_task(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    project_id: UUID,
    title: str,
    description: Optional[str],
    status: str,
    priority: str,
    activity_id: Optional[UUID],
    work_plan_id: Optional[UUID],
    assignee_id: Optional[UUID],
    due_date: Optional[date],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Task:
    await get_project(db, organization_id, project_id)
    if activity_id:
        activity = await get_activity(db, organization_id, activity_id)
        if activity.project_id != project_id:
            raise ConflictError("Activity does not belong to this project")
    if work_plan_id:
        plan = await get_work_plan(db, organization_id, work_plan_id)
        if plan.project_id != project_id:
            raise ConflictError("Work plan does not belong to this project")

    task = Task(
        organization_id=organization_id,
        project_id=project_id,
        activity_id=activity_id,
        work_plan_id=work_plan_id,
        title=title.strip(),
        description=description,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
        completed_at=utcnow() if status == "done" else None,
        created_by_id=actor_id,
    )
    db.add(task)
    await db.flush()
    await write_audit_log(
        db,
        action="tasks.create",
        resource_type="task",
        resource_id=task.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created task {task.title}",
        changes={"project_id": str(project_id), "title": task.title},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return task


async def get_task(db: AsyncSession, organization_id: UUID, task_id: UUID) -> Task:
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.organization_id == organization_id)
    )
    if not task:
        raise NotFoundError("Task not found")
    return task


async def update_task(
    db: AsyncSession,
    task: Task,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Task:
    if "activity_id" in data and data["activity_id"]:
        activity = await get_activity(db, task.organization_id, data["activity_id"])
        if activity.project_id != task.project_id:
            raise ConflictError("Activity does not belong to this project")
    if "work_plan_id" in data and data["work_plan_id"]:
        plan = await get_work_plan(db, task.organization_id, data["work_plan_id"])
        if plan.project_id != task.project_id:
            raise ConflictError("Work plan does not belong to this project")

    for key, value in data.items():
        setattr(task, key, value)

    if "status" in data:
        if data["status"] == "done" and not task.completed_at:
            task.completed_at = utcnow()
        elif data["status"] != "done":
            task.completed_at = None

    await db.flush()
    await write_audit_log(
        db,
        action="tasks.update",
        resource_type="task",
        resource_id=task.id,
        organization_id=task.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated task {task.title}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return task


async def delete_task(
    db: AsyncSession,
    task: Task,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="tasks.delete",
        resource_type="task",
        resource_id=task.id,
        organization_id=task.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted task {task.title}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(task)
    await db.flush()


async def phase2_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    programs = await db.scalar(
        select(func.count()).select_from(Program).where(Program.organization_id == organization_id)
    )
    projects = await db.scalar(
        select(func.count()).select_from(Project).where(Project.organization_id == organization_id)
    )
    activities = await db.scalar(
        select(func.count())
        .select_from(Activity)
        .where(Activity.organization_id == organization_id)
    )
    tasks = await db.scalar(
        select(func.count()).select_from(Task).where(Task.organization_id == organization_id)
    )
    open_tasks = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.organization_id == organization_id,
            Task.status.in_(["todo", "in_progress", "blocked"]),
        )
    )
    return {
        "programs_count": programs or 0,
        "projects_count": projects or 0,
        "activities_count": activities or 0,
        "tasks_count": tasks or 0,
        "open_tasks_count": open_tasks or 0,
    }
