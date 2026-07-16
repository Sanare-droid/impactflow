"""Dynamic forms / surveys API — thin HTTP layer over app.services.surveys."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import AppError, NotFoundError
from app.db.session import get_db
from app.schemas import ORMModel, PaginatedResponse, PaginationMeta
from app.services import form_schema
from app.services import surveys as survey_service

router = APIRouter(tags=["Surveys"])

READ_PERMS = ("surveys:read", "surveys:manage")
MANAGE_PERMS = ("surveys:manage",)
SUBMIT_PERMS = ("surveys:submit", "surveys:manage", "surveys:read")


# -------- Request / response models --------


class SurveyCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default="draft", max_length=32)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    is_anonymous: bool = False
    response_limit: Optional[int] = Field(default=None, ge=1)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    form_schema: Optional[dict[str, Any]] = Field(default=None, alias="schema")
    metadata: Optional[dict[str, Any]] = None


class SurveyUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=128)
    status: Optional[str] = Field(default=None, max_length=32)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    is_anonymous: Optional[bool] = None
    response_limit: Optional[int] = Field(default=None, ge=1)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    form_schema: Optional[dict[str, Any]] = Field(default=None, alias="schema")
    publish: Optional[bool] = None
    changelog: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ImportSchemaRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    form_schema: dict[str, Any] = Field(alias="schema")
    changelog: Optional[str] = None


class SurveyOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    current_version: int
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    is_anonymous: bool
    response_limit: Optional[int] = None
    starts_at: Optional[Any] = None
    ends_at: Optional[Any] = None
    cloned_from_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class AssignmentCreateRequest(BaseModel):
    target_type: str = Field(min_length=2, max_length=32)
    target_id: UUID
    status: str = Field(default="active", max_length=32)
    due_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class AssignmentOut(ORMModel):
    id: UUID
    organization_id: UUID
    survey_id: UUID
    target_type: str
    target_id: UUID
    status: str
    due_at: Optional[Any] = None
    assigned_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class ResponseSubmitRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="submitted", max_length=32)
    respondent_name: Optional[str] = None
    beneficiary_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    household_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    location: Optional[dict[str, Any]] = None
    client_mutation_id: Optional[str] = Field(default=None, max_length=64)


class ResponseUpdateRequest(BaseModel):
    answers: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(default=None, max_length=32)
    respondent_name: Optional[str] = None
    beneficiary_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    household_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    location: Optional[dict[str, Any]] = None


class ResponseOut(ORMModel):
    id: UUID
    organization_id: UUID
    survey_id: UUID
    survey_version_id: UUID
    version: int
    status: str
    answers: dict
    respondent_name: Optional[str] = None
    beneficiary_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    household_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    client_mutation_id: Optional[str] = None
    location: Optional[dict] = None
    submitted_at: Optional[Any] = None
    submitted_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class AttachmentCreateRequest(BaseModel):
    field_id: str = Field(min_length=1, max_length=128)
    file_name: str = Field(min_length=1, max_length=255)
    storage_url: str = Field(min_length=1)
    content_type: Optional[str] = Field(default=None, max_length=128)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[dict[str, Any]] = None


class AttachmentOut(ORMModel):
    id: UUID
    response_id: UUID
    field_id: str
    file_name: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_url: str
    created_at: Any


class FieldTypeOut(BaseModel):
    code: str
    label: str
    category: str


class SurveyAnalyticsOut(BaseModel):
    survey_id: str
    total_responses: int
    status_counts: dict[str, int]
    field_histograms: dict[str, Any]


# -------- Helpers --------


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


def _version_payload(version) -> dict[str, Any]:
    return {
        "id": str(version.id),
        "survey_id": str(version.survey_id),
        "version": version.version,
        "title": version.title,
        "schema": form_schema.schema_with_flat_fields(version.schema_ or {}),
        "changelog": version.changelog,
        "published_at": version.published_at,
        "created_at": version.created_at,
    }


# -------- Field types --------


@router.get("/surveys/field-types", response_model=list[FieldTypeOut])
async def get_field_types(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
) -> list[FieldTypeOut]:
    return [FieldTypeOut(**item) for item in form_schema.list_field_types()]


# -------- Surveys --------


@router.get("/surveys", response_model=PaginatedResponse[SurveyOut])
async def list_surveys(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    search: Optional[str] = None,
    updated_after: Optional[datetime] = None,
) -> PaginatedResponse[SurveyOut]:
    org_id = _require_org(ctx)
    items, total = await survey_service.list_surveys(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        program_id=program_id,
        project_id=project_id,
        search=search,
        updated_after=updated_after,
    )
    return PaginatedResponse(
        items=[SurveyOut.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/surveys", response_model=SurveyOut, status_code=status.HTTP_201_CREATED)
async def create_survey(
    body: SurveyCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await survey_service.create_survey(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_none=True, by_alias=True),
        ip_address=ip,
        user_agent=ua,
    )
    return SurveyOut.model_validate(row)


@router.get("/surveys/{survey_id}", response_model=dict)
async def get_survey(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    version = await survey_service.get_current_version(db, survey)
    return {
        "survey": SurveyOut.model_validate(survey).model_dump(),
        "version": _version_payload(version),
    }


@router.patch("/surveys/{survey_id}", response_model=SurveyOut)
async def update_survey(
    survey_id: UUID,
    body: SurveyUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    updated = await survey_service.update_survey(
        db,
        survey,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_none=True, by_alias=True),
        ip_address=ip,
        user_agent=ua,
    )
    return SurveyOut.model_validate(updated)


@router.post("/surveys/{survey_id}/clone", response_model=SurveyOut, status_code=status.HTTP_201_CREATED)
async def clone_survey(
    survey_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    clone = await survey_service.clone_survey(
        db,
        survey,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return SurveyOut.model_validate(clone)


@router.post("/surveys/{survey_id}/archive", response_model=SurveyOut)
async def archive_survey(
    survey_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    archived = await survey_service.archive_survey(
        db,
        survey,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return SurveyOut.model_validate(archived)


@router.get("/surveys/{survey_id}/versions", response_model=list[dict])
async def list_survey_versions(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    org_id = _require_org(ctx)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    versions = await survey_service.list_versions(db, survey)
    return [_version_payload(v) for v in versions]


@router.get("/surveys/{survey_id}/versions/{version}", response_model=dict)
async def get_survey_version(
    survey_id: UUID,
    version: int,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    row = await survey_service.get_version(db, org_id, survey_id, version)
    return _version_payload(row)


@router.get("/surveys/{survey_id}/export-schema")
async def export_survey_schema(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    org_id = _require_org(ctx)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    version = await survey_service.get_current_version(db, survey)
    payload = {
        "name": survey.name,
        "code": survey.code,
        "category": survey.category,
        "schema": form_schema.schema_with_flat_fields(version.schema_ or {}),
    }
    body = json.dumps(payload, indent=2, default=str)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{survey.code}-schema.json"'},
    )


@router.post("/surveys/{survey_id}/import-schema", response_model=dict)
async def import_survey_schema(
    survey_id: UUID,
    body: ImportSchemaRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    updated = await survey_service.update_survey(
        db,
        survey,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data={"schema": body.form_schema, "changelog": body.changelog},
        ip_address=ip,
        user_agent=ua,
    )
    version = await survey_service.get_current_version(db, updated)
    return {
        "survey": SurveyOut.model_validate(updated).model_dump(),
        "version": _version_payload(version),
    }


# -------- Assignments --------


@router.get("/surveys/{survey_id}/assignments", response_model=list[AssignmentOut])
async def list_survey_assignments(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AssignmentOut]:
    org_id = _require_org(ctx)
    await survey_service.get_survey(db, org_id, survey_id)
    rows = await survey_service.list_assignments(db, org_id, survey_id)
    return [AssignmentOut.model_validate(r) for r in rows]


@router.post(
    "/surveys/{survey_id}/assignments",
    response_model=AssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_survey_assignment(
    survey_id: UUID,
    body: AssignmentCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssignmentOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    row = await survey_service.create_assignment(
        db,
        survey,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    return AssignmentOut.model_validate(row)


@router.delete("/surveys/{survey_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey_assignment(
    survey_id: UUID,
    assignment_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*MANAGE_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    assignment = await survey_service.get_assignment(db, org_id, survey_id, assignment_id)
    await survey_service.delete_assignment(
        db,
        assignment,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------- Responses --------


@router.post(
    "/surveys/{survey_id}/responses",
    response_model=ResponseOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_survey_response(
    survey_id: UUID,
    body: ResponseSubmitRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SUBMIT_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await survey_service.submit_response(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        survey_id=survey_id,
        data=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ResponseOut.model_validate(row)


@router.patch("/survey-responses/{response_id}", response_model=ResponseOut)
async def update_survey_response(
    response_id: UUID,
    body: ResponseUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SUBMIT_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    response = await survey_service.get_response(db, org_id, response_id)
    updated = await survey_service.update_response(
        db,
        response,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_none=True),
        ip_address=ip,
        user_agent=ua,
    )
    return ResponseOut.model_validate(updated)


@router.get("/survey-responses", response_model=PaginatedResponse[ResponseOut])
async def list_survey_responses(
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    survey_id: Optional[UUID] = None,
    status: Optional[str] = None,
    beneficiary_id: Optional[UUID] = None,
    community_id: Optional[UUID] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    updated_after: Optional[datetime] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ResponseOut]:
    org_id = _require_org(ctx)
    items, total = await survey_service.list_responses(
        db,
        org_id,
        survey_id=survey_id,
        status=status,
        beneficiary_id=beneficiary_id,
        community_id=community_id,
        program_id=program_id,
        project_id=project_id,
        updated_after=updated_after,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[ResponseOut.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


# -------- Analytics / Export --------


@router.get("/surveys/{survey_id}/analytics", response_model=SurveyAnalyticsOut)
async def get_survey_analytics(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyAnalyticsOut:
    org_id = _require_org(ctx)
    data = await survey_service.response_analytics(db, org_id, survey_id)
    return SurveyAnalyticsOut(**data)


@router.get("/surveys/{survey_id}/export")
async def export_survey_responses(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions(*READ_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("csv"),
) -> Response:
    org_id = _require_org(ctx)
    await survey_service.get_survey(db, org_id, survey_id)
    fmt = format.lower()
    if fmt == "csv":
        body = await survey_service.export_responses_csv(db, org_id, survey_id)
        return PlainTextResponse(
            body,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="survey-{survey_id}-responses.csv"'},
        )
    if fmt in {"html", "pdf"}:
        # HTML is print-to-PDF friendly; clients may request format=pdf for the same payload.
        body = await survey_service.export_responses_html(db, org_id, survey_id)
        return PlainTextResponse(
            body,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="survey-{survey_id}-responses.html"'},
        )
    if fmt in {"xlsx", "excel", "xls"}:
        body = await survey_service.export_responses_excel_xml(db, org_id, survey_id)
        return PlainTextResponse(
            body,
            media_type="application/vnd.ms-excel",
            headers={"Content-Disposition": f'attachment; filename="survey-{survey_id}-responses.xls"'},
        )
    raise AppError("Unsupported export format", code="VALIDATION_ERROR", status_code=422)


# -------- Attachments --------


@router.post(
    "/survey-responses/{response_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_response_attachment(
    response_id: UUID,
    body: AttachmentCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions(*SUBMIT_PERMS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttachmentOut:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    response = await survey_service.get_response(db, org_id, response_id)
    row = await survey_service.add_attachment(
        db,
        response,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        field_id=body.field_id,
        file_name=body.file_name,
        storage_url=body.storage_url,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        metadata=body.metadata,
        ip_address=ip,
        user_agent=ua,
    )
    return AttachmentOut.model_validate(row)
