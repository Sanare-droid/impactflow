"""Survey CRUD, versioning, and response capture."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.db.base import utcnow
from app.models.survey import Survey, SurveyResponse, SurveyVersion
from app.services.audit import write_audit_log
from app.services.programs import _ensure_unique_code, make_code

DEFAULT_SCHEMA = {
    "fields": [
        {"id": "q1", "type": "text", "label": "Full name", "required": True},
        {
            "id": "q2",
            "type": "select",
            "label": "Household status",
            "required": False,
            "options": ["stable", "displaced", "host"],
        },
        {"id": "q3", "type": "textarea", "label": "Notes", "required": False},
    ]
}


async def get_survey(db: AsyncSession, organization_id: UUID, survey_id: UUID) -> Survey:
    row = await db.scalar(
        select(Survey).where(Survey.id == survey_id, Survey.organization_id == organization_id)
    )
    if not row:
        raise NotFoundError("Survey not found")
    return row


async def list_surveys(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Survey], int]:
    filters = [Survey.organization_id == organization_id]
    if status:
        filters.append(Survey.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(Survey.name.ilike(like), Survey.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Survey).where(*filters)) or 0
    rows = await db.scalars(
        select(Survey)
        .where(*filters)
        .order_by(Survey.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def create_survey(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Survey:
    code = await _ensure_unique_code(
        db,
        model=Survey,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="SRV-"),
    )
    survey = Survey(
        organization_id=organization_id,
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        status=data.get("status") or "draft",
        current_version=1,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        created_by_id=actor_id,
        metadata_=data.get("metadata") or {},
    )
    db.add(survey)
    await db.flush()
    schema = data.get("schema") or DEFAULT_SCHEMA
    version = SurveyVersion(
        organization_id=organization_id,
        survey_id=survey.id,
        version=1,
        title=survey.name,
        schema_=schema,
        created_by_id=actor_id,
    )
    if survey.status == "published":
        version.published_at = utcnow()
    db.add(version)
    await db.flush()
    await write_audit_log(
        db,
        action="surveys.create",
        resource_type="survey",
        resource_id=survey.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created survey {survey.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return survey


async def update_survey(
    db: AsyncSession,
    survey: Survey,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Survey:
    schema = data.pop("schema", None)
    publish = data.pop("publish", None)
    for key, value in data.items():
        if key == "metadata" and value is not None:
            survey.metadata_ = value
        elif value is not None and hasattr(survey, key):
            setattr(survey, key, value)

    if schema is not None:
        next_version = survey.current_version + 1
        version = SurveyVersion(
            organization_id=survey.organization_id,
            survey_id=survey.id,
            version=next_version,
            title=survey.name,
            schema_=schema,
            created_by_id=actor_id,
        )
        survey.current_version = next_version
        db.add(version)
        await db.flush()

    if publish is True or survey.status == "published":
        survey.status = "published"
        ver = await get_current_version(db, survey)
        ver.published_at = utcnow()

    await db.flush()
    await write_audit_log(
        db,
        action="surveys.update",
        resource_type="survey",
        resource_id=survey.id,
        organization_id=survey.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated survey {survey.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return survey


async def get_current_version(db: AsyncSession, survey: Survey) -> SurveyVersion:
    row = await db.scalar(
        select(SurveyVersion).where(
            SurveyVersion.survey_id == survey.id,
            SurveyVersion.version == survey.current_version,
        )
    )
    if not row:
        raise NotFoundError("Survey version not found")
    return row


async def list_responses(
    db: AsyncSession,
    organization_id: UUID,
    *,
    survey_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SurveyResponse], int]:
    filters = [SurveyResponse.organization_id == organization_id]
    if survey_id:
        filters.append(SurveyResponse.survey_id == survey_id)
    total = await db.scalar(select(func.count()).select_from(SurveyResponse).where(*filters)) or 0
    rows = await db.scalars(
        select(SurveyResponse)
        .where(*filters)
        .order_by(SurveyResponse.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def submit_response(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    survey_id: UUID,
    answers: dict,
    respondent_name: Optional[str] = None,
    beneficiary_id: Optional[UUID] = None,
    community_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SurveyResponse:
    survey = await get_survey(db, organization_id, survey_id)
    if survey.status not in ("published", "draft"):
        raise AppError("Survey is not accepting responses", code="survey_closed")
    version = await get_current_version(db, survey)
    row = SurveyResponse(
        organization_id=organization_id,
        survey_id=survey.id,
        survey_version_id=version.id,
        version=version.version,
        status="submitted",
        answers=answers or {},
        respondent_name=respondent_name,
        beneficiary_id=beneficiary_id,
        community_id=community_id,
        submitted_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="surveys.response",
        resource_type="survey_response",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Submitted response for {survey.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def phase11_survey_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    total = await db.scalar(
        select(func.count()).select_from(Survey).where(Survey.organization_id == organization_id)
    )
    published = await db.scalar(
        select(func.count())
        .select_from(Survey)
        .where(Survey.organization_id == organization_id, Survey.status == "published")
    )
    responses = await db.scalar(
        select(func.count())
        .select_from(SurveyResponse)
        .where(SurveyResponse.organization_id == organization_id)
    )
    return {
        "surveys_count": total or 0,
        "published_surveys_count": published or 0,
        "survey_responses_count": responses or 0,
    }
