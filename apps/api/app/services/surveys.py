"""Survey / dynamic form CRUD, versioning, assignments, and response capture."""

from __future__ import annotations

import csv
import io
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.db.base import utcnow
from app.models.survey import (
    Survey,
    SurveyAnswer,
    SurveyAssignment,
    SurveyResponse,
    SurveyResponseAttachment,
    SurveyVersion,
)
from app.services import events as events_service
from app.services import form_schema
from app.services.audit import write_audit_log
from app.services.beneficiaries import get_beneficiary, get_community, get_household
from app.services.programs import _ensure_unique_code, get_activity, get_program, get_project, make_code

DEFAULT_SCHEMA = form_schema.DEFAULT_SCHEMA_V2

NUMERIC_FIELD_TYPES = {"number", "decimal", "currency", "rating", "slider"}
JSON_FIELD_TYPES = {"multi_select", "gps", "image", "video", "audio", "file", "matrix", "repeat_group"}
CHOICE_HISTOGRAM_TYPES = {"radio", "dropdown", "boolean", "checkbox"}

ASSIGNMENT_TARGET_TYPES = {"program", "project", "activity", "beneficiary", "community", "household"}


# -------- Internal helpers --------


async def _assert_related_entities(
    db: AsyncSession,
    organization_id: UUID,
    *,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    activity_id: Optional[UUID] = None,
) -> None:
    if program_id:
        await get_program(db, organization_id, program_id)
    if project_id:
        await get_project(db, organization_id, project_id)
    if activity_id:
        await get_activity(db, organization_id, activity_id)


async def _assert_assignment_target(
    db: AsyncSession, organization_id: UUID, target_type: str, target_id: UUID
) -> None:
    if target_type not in ASSIGNMENT_TARGET_TYPES:
        raise AppError(
            f"Unsupported target_type: {target_type}",
            code="VALIDATION_ERROR",
            status_code=422,
        )
    if target_type == "program":
        await get_program(db, organization_id, target_id)
    elif target_type == "project":
        await get_project(db, organization_id, target_id)
    elif target_type == "activity":
        await get_activity(db, organization_id, target_id)
    elif target_type == "beneficiary":
        await get_beneficiary(db, organization_id, target_id)
    elif target_type == "community":
        await get_community(db, organization_id, target_id)
    elif target_type == "household":
        await get_household(db, organization_id, target_id)


async def _emit_event_safe(db: AsyncSession, **kwargs: Any) -> None:
    """Emit a domain event without letting notification/webhook issues break the request."""
    try:
        await events_service.emit_event(db, **kwargs)
    except Exception:  # noqa: BLE001
        pass


def _answer_columns(ftype: str, value: Any) -> tuple[Optional[str], Optional[str], Optional[Any]]:
    """Return (value_text, value_number, value_json) for a normalized answer value."""
    if value is None:
        return None, None, None
    if ftype in NUMERIC_FIELD_TYPES:
        return None, str(value), None
    if ftype in JSON_FIELD_TYPES:
        return None, None, value
    if isinstance(value, bool):
        return str(value).lower(), None, None
    return str(value), None, None


async def _upsert_answers(
    db: AsyncSession,
    response: SurveyResponse,
    survey_id: UUID,
    schema: dict[str, Any],
    answers: dict[str, Any],
) -> None:
    fields_by_id = {f["id"]: f for f in form_schema.iter_fields(schema)}
    existing_rows = list(
        await db.scalars(select(SurveyAnswer).where(SurveyAnswer.response_id == response.id))
    )
    existing_by_field = {row.field_id: row for row in existing_rows}

    for field_id, value in answers.items():
        field = fields_by_id.get(field_id, {})
        ftype = form_schema.normalize_field_type(str(field.get("type") or "text"))
        value_text, value_number, value_json = _answer_columns(ftype, value)
        row = existing_by_field.get(field_id)
        if row:
            row.field_type = ftype
            row.value_text = value_text
            row.value_number = value_number
            row.value_json = value_json
        else:
            db.add(
                SurveyAnswer(
                    organization_id=response.organization_id,
                    response_id=response.id,
                    survey_id=survey_id,
                    field_id=field_id,
                    field_type=ftype,
                    value_text=value_text,
                    value_number=value_number,
                    value_json=value_json,
                )
            )

    for field_id, row in existing_by_field.items():
        if field_id not in answers:
            await db.delete(row)

    await db.flush()


# -------- Surveys --------


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
    category: Optional[str] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    search: Optional[str] = None,
    updated_after: Optional[datetime] = None,
) -> tuple[list[Survey], int]:
    filters = [Survey.organization_id == organization_id]
    if status:
        filters.append(Survey.status == status)
    if category:
        filters.append(Survey.category == category)
    if program_id:
        filters.append(Survey.program_id == program_id)
    if project_id:
        filters.append(Survey.project_id == project_id)
    if updated_after:
        filters.append(Survey.updated_at >= updated_after)
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
    await _assert_related_entities(
        db,
        organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        activity_id=data.get("activity_id"),
    )

    code = await _ensure_unique_code(
        db,
        model=Survey,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="SRV-"),
    )
    status = data.get("status") or "draft"
    schema = form_schema.normalize_schema(data.get("schema"))

    survey = Survey(
        organization_id=organization_id,
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        category=data.get("category"),
        status=status,
        current_version=1,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        activity_id=data.get("activity_id"),
        is_anonymous=bool(data.get("is_anonymous") or False),
        response_limit=data.get("response_limit"),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
        created_by_id=actor_id,
        metadata_=data.get("metadata") or {},
    )
    db.add(survey)
    await db.flush()

    version = SurveyVersion(
        organization_id=organization_id,
        survey_id=survey.id,
        version=1,
        title=survey.name,
        schema_=schema,
        created_by_id=actor_id,
    )
    if status == "published":
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

    if status == "published":
        await _emit_event_safe(
            db,
            organization_id=organization_id,
            event_type="survey.published",
            title=f"Survey published: {survey.name}",
            resource_type="survey",
            resource_id=str(survey.id),
            exclude_user_id=actor_id,
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
    changelog = data.pop("changelog", None)

    await _assert_related_entities(
        db,
        survey.organization_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        activity_id=data.get("activity_id"),
    )

    for key, value in data.items():
        if key == "metadata" and value is not None:
            survey.metadata_ = value
        elif value is not None and hasattr(survey, key):
            setattr(survey, key, value)

    if schema is not None:
        next_version = survey.current_version + 1
        normalized = form_schema.normalize_schema(schema)
        version = SurveyVersion(
            organization_id=survey.organization_id,
            survey_id=survey.id,
            version=next_version,
            title=survey.name,
            schema_=normalized,
            changelog=changelog,
            created_by_id=actor_id,
        )
        survey.current_version = next_version
        db.add(version)
        await db.flush()

    if publish is True:
        survey.status = "published"

    newly_published = False
    if survey.status == "published":
        current_version = await get_current_version(db, survey)
        if not current_version.published_at:
            current_version.published_at = utcnow()
            newly_published = True

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

    if newly_published:
        await _emit_event_safe(
            db,
            organization_id=survey.organization_id,
            event_type="survey.published",
            title=f"Survey published: {survey.name}",
            resource_type="survey",
            resource_id=str(survey.id),
            exclude_user_id=actor_id,
        )

    return survey


async def clone_survey(
    db: AsyncSession,
    survey: Survey,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Survey:
    source_version = await get_current_version(db, survey)
    new_code = await _ensure_unique_code(
        db,
        model=Survey,
        organization_id=survey.organization_id,
        code=make_code(survey.name, prefix="SRV-"),
    )
    clone = Survey(
        organization_id=survey.organization_id,
        name=f"{survey.name} (Copy)",
        code=new_code,
        description=survey.description,
        category=survey.category,
        status="draft",
        current_version=1,
        program_id=survey.program_id,
        project_id=survey.project_id,
        activity_id=survey.activity_id,
        is_anonymous=survey.is_anonymous,
        response_limit=survey.response_limit,
        cloned_from_id=survey.id,
        created_by_id=actor_id,
        metadata_=dict(survey.metadata_ or {}),
    )
    db.add(clone)
    await db.flush()

    version = SurveyVersion(
        organization_id=survey.organization_id,
        survey_id=clone.id,
        version=1,
        title=clone.name,
        schema_=deepcopy(source_version.schema_),
        created_by_id=actor_id,
    )
    db.add(version)
    await db.flush()

    await write_audit_log(
        db,
        action="surveys.clone",
        resource_type="survey",
        resource_id=clone.id,
        organization_id=survey.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Cloned survey {survey.code} into {clone.code}",
        changes={"cloned_from_id": str(survey.id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return clone


async def archive_survey(
    db: AsyncSession,
    survey: Survey,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Survey:
    survey.status = "archived"
    await db.flush()
    await write_audit_log(
        db,
        action="surveys.archive",
        resource_type="survey",
        resource_id=survey.id,
        organization_id=survey.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Archived survey {survey.code}",
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


async def list_versions(db: AsyncSession, survey: Survey) -> list[SurveyVersion]:
    rows = await db.scalars(
        select(SurveyVersion)
        .where(SurveyVersion.survey_id == survey.id)
        .order_by(SurveyVersion.version.desc())
    )
    return list(rows)


async def get_version(
    db: AsyncSession, organization_id: UUID, survey_id: UUID, version: int
) -> SurveyVersion:
    row = await db.scalar(
        select(SurveyVersion).where(
            SurveyVersion.survey_id == survey_id,
            SurveyVersion.organization_id == organization_id,
            SurveyVersion.version == version,
        )
    )
    if not row:
        raise NotFoundError("Survey version not found")
    return row


# -------- Assignments --------


async def create_assignment(
    db: AsyncSession,
    survey: Survey,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SurveyAssignment:
    target_type = str(data["target_type"]).strip().lower()
    target_id = data["target_id"]
    await _assert_assignment_target(db, survey.organization_id, target_type, target_id)

    row = SurveyAssignment(
        organization_id=survey.organization_id,
        survey_id=survey.id,
        target_type=target_type,
        target_id=target_id,
        status=data.get("status") or "active",
        due_at=data.get("due_at"),
        assigned_by_id=actor_id,
        metadata_=data.get("metadata") or {},
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="surveys.assignment.create",
        resource_type="survey_assignment",
        resource_id=row.id,
        organization_id=survey.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Assigned survey {survey.code} to {target_type}:{target_id}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


async def list_assignments(
    db: AsyncSession, organization_id: UUID, survey_id: UUID
) -> list[SurveyAssignment]:
    rows = await db.scalars(
        select(SurveyAssignment)
        .where(
            SurveyAssignment.organization_id == organization_id,
            SurveyAssignment.survey_id == survey_id,
        )
        .order_by(SurveyAssignment.created_at.desc())
    )
    return list(rows)


async def get_assignment(
    db: AsyncSession, organization_id: UUID, survey_id: UUID, assignment_id: UUID
) -> SurveyAssignment:
    row = await db.scalar(
        select(SurveyAssignment).where(
            SurveyAssignment.id == assignment_id,
            SurveyAssignment.organization_id == organization_id,
            SurveyAssignment.survey_id == survey_id,
        )
    )
    if not row:
        raise NotFoundError("Survey assignment not found")
    return row


async def delete_assignment(
    db: AsyncSession,
    assignment: SurveyAssignment,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="surveys.assignment.delete",
        resource_type="survey_assignment",
        resource_id=assignment.id,
        organization_id=assignment.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Removed survey assignment {assignment.id}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(assignment)
    await db.flush()


# -------- Responses --------


async def get_response(
    db: AsyncSession, organization_id: UUID, response_id: UUID
) -> SurveyResponse:
    row = await db.scalar(
        select(SurveyResponse).where(
            SurveyResponse.id == response_id,
            SurveyResponse.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Survey response not found")
    return row


async def submit_response(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    survey_id: UUID,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SurveyResponse:
    # client_mutation_id must normalize "" -> None so the org-scoped unique
    # constraint doesn't collide across unrelated draft submissions on SQLite/Postgres.
    client_mutation_id = (data.get("client_mutation_id") or "").strip() or None
    if client_mutation_id:
        existing = await db.scalar(
            select(SurveyResponse).where(
                SurveyResponse.organization_id == organization_id,
                SurveyResponse.client_mutation_id == client_mutation_id,
            )
        )
        if existing:
            return existing

    survey = await get_survey(db, organization_id, survey_id)
    status = data.get("status") or "submitted"
    if status not in ("draft", "submitted"):
        raise AppError("Invalid response status", code="VALIDATION_ERROR", status_code=422)

    if survey.status != "published":
        raise AppError("Survey is not accepting responses", code="survey_closed")

    now = utcnow()
    if survey.starts_at and now < survey.starts_at:
        raise AppError("Survey has not opened yet", code="survey_not_open")
    if survey.ends_at and now > survey.ends_at:
        raise AppError("Survey has closed", code="survey_closed")

    if status == "submitted" and survey.response_limit:
        current_count = (
            await db.scalar(
                select(func.count())
                .select_from(SurveyResponse)
                .where(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.status == "submitted",
                )
            )
            or 0
        )
        if current_count >= survey.response_limit:
            raise AppError("Survey response limit reached", code="response_limit_reached")

    version = await get_current_version(db, survey)
    partial = status == "draft"
    cleaned_answers = form_schema.validate_answers(
        version.schema_, data.get("answers") or {}, partial=partial
    )

    program_id = data.get("program_id")
    project_id = data.get("project_id")
    activity_id = data.get("activity_id")
    household_id = data.get("household_id")
    beneficiary_id = data.get("beneficiary_id")
    community_id = data.get("community_id")
    assignment_id = data.get("assignment_id")

    await _assert_related_entities(
        db, organization_id, program_id=program_id, project_id=project_id, activity_id=activity_id
    )
    if household_id:
        await get_household(db, organization_id, household_id)
    if beneficiary_id:
        await get_beneficiary(db, organization_id, beneficiary_id)
    if community_id:
        await get_community(db, organization_id, community_id)
    if assignment_id:
        await get_assignment(db, organization_id, survey.id, assignment_id)

    row = SurveyResponse(
        organization_id=organization_id,
        survey_id=survey.id,
        survey_version_id=version.id,
        version=version.version,
        status=status,
        answers=cleaned_answers,
        respondent_name=data.get("respondent_name"),
        beneficiary_id=beneficiary_id,
        community_id=community_id,
        household_id=household_id,
        program_id=program_id,
        project_id=project_id,
        activity_id=activity_id,
        assignment_id=assignment_id,
        client_mutation_id=client_mutation_id,
        location=data.get("location"),
        submitted_at=now if status == "submitted" else None,
        submitted_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await _upsert_answers(db, row, survey.id, version.schema_, cleaned_answers)

    await write_audit_log(
        db,
        action="surveys.response.submit" if status == "submitted" else "surveys.response.draft",
        resource_type="survey_response",
        resource_id=row.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=(
            f"Submitted response for {survey.code}"
            if status == "submitted"
            else f"Saved draft response for {survey.code}"
        ),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if status == "submitted":
        await _emit_event_safe(
            db,
            organization_id=organization_id,
            event_type="survey.response_submitted",
            title=f"New response for {survey.name}",
            body=data.get("respondent_name"),
            resource_type="survey_response",
            resource_id=str(row.id),
            exclude_user_id=actor_id,
        )

    return row


async def update_response(
    db: AsyncSession,
    response: SurveyResponse,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SurveyResponse:
    survey = await get_survey(db, response.organization_id, response.survey_id)
    version = await db.get(SurveyVersion, response.survey_version_id)
    if not version:
        raise NotFoundError("Survey version not found")

    new_status = data.get("status") or response.status
    if new_status not in ("draft", "submitted"):
        raise AppError("Invalid response status", code="VALIDATION_ERROR", status_code=422)
    partial = new_status == "draft"

    if "answers" in data:
        merged_answers = {**(response.answers or {}), **(data.get("answers") or {})}
    else:
        merged_answers = dict(response.answers or {})
    cleaned_answers = form_schema.validate_answers(version.schema_, merged_answers, partial=partial)

    became_submitted = new_status == "submitted" and response.status != "submitted"
    if became_submitted and survey.response_limit:
        current_count = (
            await db.scalar(
                select(func.count())
                .select_from(SurveyResponse)
                .where(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.status == "submitted",
                    SurveyResponse.id != response.id,
                )
            )
            or 0
        )
        if current_count >= survey.response_limit:
            raise AppError("Survey response limit reached", code="response_limit_reached")

    for key in (
        "respondent_name",
        "location",
        "beneficiary_id",
        "community_id",
        "household_id",
        "program_id",
        "project_id",
        "activity_id",
    ):
        if key in data:
            setattr(response, key, data[key])

    response.answers = cleaned_answers
    response.status = new_status
    if became_submitted:
        response.submitted_at = utcnow()
        response.submitted_by_id = actor_id

    await db.flush()
    await _upsert_answers(db, response, survey.id, version.schema_, cleaned_answers)

    await write_audit_log(
        db,
        action="surveys.response.update",
        resource_type="survey_response",
        resource_id=response.id,
        organization_id=response.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated response for {survey.code}",
        changes={k: v for k, v in data.items() if k != "answers"},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if became_submitted:
        await _emit_event_safe(
            db,
            organization_id=response.organization_id,
            event_type="survey.response_submitted",
            title=f"New response for {survey.name}",
            body=response.respondent_name,
            resource_type="survey_response",
            resource_id=str(response.id),
            exclude_user_id=actor_id,
        )

    return response


async def list_responses(
    db: AsyncSession,
    organization_id: UUID,
    *,
    survey_id: Optional[UUID] = None,
    status: Optional[str] = None,
    beneficiary_id: Optional[UUID] = None,
    community_id: Optional[UUID] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    updated_after: Optional[datetime] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SurveyResponse], int]:
    filters = [SurveyResponse.organization_id == organization_id]
    if survey_id:
        filters.append(SurveyResponse.survey_id == survey_id)
    if status:
        filters.append(SurveyResponse.status == status)
    if beneficiary_id:
        filters.append(SurveyResponse.beneficiary_id == beneficiary_id)
    if community_id:
        filters.append(SurveyResponse.community_id == community_id)
    if program_id:
        filters.append(SurveyResponse.program_id == program_id)
    if project_id:
        filters.append(SurveyResponse.project_id == project_id)
    if updated_after:
        filters.append(SurveyResponse.updated_at >= updated_after)
    if date_from:
        filters.append(SurveyResponse.created_at >= date_from)
    if date_to:
        filters.append(SurveyResponse.created_at <= date_to)

    total = await db.scalar(select(func.count()).select_from(SurveyResponse).where(*filters)) or 0
    rows = await db.scalars(
        select(SurveyResponse)
        .where(*filters)
        .order_by(SurveyResponse.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


# -------- Analytics / Export --------


async def response_analytics(db: AsyncSession, organization_id: UUID, survey_id: UUID) -> dict[str, Any]:
    survey = await get_survey(db, organization_id, survey_id)
    version = await get_current_version(db, survey)
    fields = form_schema.iter_fields(version.schema_)

    status_result = await db.execute(
        select(SurveyResponse.status, func.count())
        .where(
            SurveyResponse.organization_id == organization_id,
            SurveyResponse.survey_id == survey_id,
        )
        .group_by(SurveyResponse.status)
    )
    status_counts: dict[str, int] = {row[0]: row[1] for row in status_result.all()}
    total_responses = sum(status_counts.values())

    field_histograms: dict[str, Any] = {}
    for field in fields:
        ftype = form_schema.normalize_field_type(str(field.get("type") or "text"))
        field_id = field["id"]
        if ftype in CHOICE_HISTOGRAM_TYPES:
            result = await db.execute(
                select(SurveyAnswer.value_text, func.count())
                .where(
                    SurveyAnswer.organization_id == organization_id,
                    SurveyAnswer.survey_id == survey_id,
                    SurveyAnswer.field_id == field_id,
                )
                .group_by(SurveyAnswer.value_text)
            )
            counts = {(key or ""): count for key, count in result.all()}
            field_histograms[field_id] = {
                "label": field.get("label") or field_id,
                "type": ftype,
                "counts": counts,
            }
        elif ftype == "multi_select":
            values = await db.scalars(
                select(SurveyAnswer.value_json).where(
                    SurveyAnswer.organization_id == organization_id,
                    SurveyAnswer.survey_id == survey_id,
                    SurveyAnswer.field_id == field_id,
                )
            )
            counts: dict[str, int] = {}
            for value in values:
                for item in value or []:
                    key = str(item)
                    counts[key] = counts.get(key, 0) + 1
            field_histograms[field_id] = {
                "label": field.get("label") or field_id,
                "type": ftype,
                "counts": counts,
            }

    return {
        "survey_id": str(survey_id),
        "total_responses": total_responses,
        "status_counts": status_counts,
        "field_histograms": field_histograms,
    }


async def export_responses_csv(db: AsyncSession, organization_id: UUID, survey_id: UUID) -> str:
    survey = await get_survey(db, organization_id, survey_id)
    version = await get_current_version(db, survey)
    fields = form_schema.iter_fields(version.schema_)
    field_ids = [f["id"] for f in fields if f.get("type") != "section_header"]

    rows = await db.scalars(
        select(SurveyResponse)
        .where(
            SurveyResponse.organization_id == organization_id,
            SurveyResponse.survey_id == survey_id,
        )
        .order_by(SurveyResponse.created_at.asc())
    )

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["response_id", "status", "respondent_name", "submitted_at", "created_at", *field_ids]
    writer.writerow(header)

    for response in rows:
        answers = response.answers or {}
        row: list[Any] = [
            str(response.id),
            response.status,
            response.respondent_name or "",
            response.submitted_at.isoformat() if response.submitted_at else "",
            response.created_at.isoformat() if response.created_at else "",
        ]
        for field_id in field_ids:
            value = answers.get(field_id, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            row.append(value if value is not None else "")
        writer.writerow(row)

    return output.getvalue()


async def export_responses_html(db: AsyncSession, organization_id: UUID, survey_id: UUID) -> str:
    """HTML table suitable for browser print-to-PDF."""
    survey = await get_survey(db, organization_id, survey_id)
    version = await get_current_version(db, survey)
    fields = [
        f for f in form_schema.iter_fields(version.schema_) if f.get("type") != "section_header"
    ]
    field_ids = [f["id"] for f in fields]
    labels = {f["id"]: str(f.get("label") or f["id"]) for f in fields}

    rows = await db.scalars(
        select(SurveyResponse)
        .where(
            SurveyResponse.organization_id == organization_id,
            SurveyResponse.survey_id == survey_id,
        )
        .order_by(SurveyResponse.created_at.asc())
    )

    def esc(value: Any) -> str:
        text = "" if value is None else str(value)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{esc(survey.name)} responses</title>",
        "<style>body{font-family:system-ui,sans-serif;padding:24px;color:#1c1917}"
        "table{border-collapse:collapse;width:100%;font-size:12px}"
        "th,td{border:1px solid #d6d3d1;padding:6px 8px;text-align:left}"
        "th{background:#f5f5f4} @media print{button{display:none}}</style>",
        "</head><body>",
        f"<h1>{esc(survey.name)}</h1>",
        f"<p>{esc(survey.code)} · printable report (use Print → Save as PDF)</p>",
        "<table><thead><tr>",
        "<th>Response</th><th>Status</th><th>Respondent</th><th>Submitted</th>",
    ]
    for fid in field_ids:
        parts.append(f"<th>{esc(labels[fid])}</th>")
    parts.append("</tr></thead><tbody>")
    for response in rows:
        answers = response.answers or {}
        parts.append("<tr>")
        parts.append(f"<td>{esc(response.id)}</td>")
        parts.append(f"<td>{esc(response.status)}</td>")
        parts.append(f"<td>{esc(response.respondent_name or '')}</td>")
        parts.append(
            f"<td>{esc(response.submitted_at.isoformat() if response.submitted_at else '')}</td>"
        )
        for field_id in field_ids:
            value = answers.get(field_id, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            parts.append(f"<td>{esc(value)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></body></html>")
    return "".join(parts)


async def export_responses_excel_xml(db: AsyncSession, organization_id: UUID, survey_id: UUID) -> str:
    """SpreadsheetML XML that Microsoft Excel opens as a workbook."""
    csv_text = await export_responses_csv(db, organization_id, survey_id)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    def cell(value: str) -> str:
        safe = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        return f'<Cell><Data ss:Type="String">{safe}</Data></Cell>'

    xml_rows = []
    for row in rows:
        xml_rows.append("<Row>" + "".join(cell(col) for col in row) + "</Row>")

    return (
        '<?xml version="1.0"?>\n'
        '<?mso-application progid="Excel.Sheet"?>\n'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        "<Worksheet ss:Name=\"Responses\"><Table>"
        + "".join(xml_rows)
        + "</Table></Worksheet></Workbook>"
    )


# -------- Attachments --------


async def add_attachment(
    db: AsyncSession,
    response: SurveyResponse,
    *,
    actor_id: UUID,
    actor_email: str,
    field_id: str,
    file_name: str,
    storage_url: str,
    content_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SurveyResponseAttachment:
    row = SurveyResponseAttachment(
        organization_id=response.organization_id,
        response_id=response.id,
        field_id=field_id,
        file_name=file_name,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_url=storage_url,
        metadata_=metadata or {},
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        action="surveys.attachment.create",
        resource_type="survey_response_attachment",
        resource_id=row.id,
        organization_id=response.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added attachment {file_name} to response {response.id}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


# -------- Dashboard counts --------


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
