from __future__ import annotations

from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import ORMModel, PaginatedResponse, PaginationMeta
from app.services import surveys as survey_service

router = APIRouter(tags=["Surveys"])


class SurveyCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    form_schema: Optional[dict[str, Any]] = Field(default=None, alias="schema")
    metadata: Optional[dict[str, Any]] = None


class SurveyUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    form_schema: Optional[dict[str, Any]] = Field(default=None, alias="schema")
    publish: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class SurveyResponseModel(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str
    current_version: int
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class SurveyVersionResponse(ORMModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: UUID
    survey_id: UUID
    version: int
    title: str
    form_schema: dict = Field(validation_alias="schema_", serialization_alias="schema")
    published_at: Optional[Any] = None
    created_at: Any


class SurveySubmissionRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    respondent_name: Optional[str] = None
    beneficiary_id: Optional[UUID] = None
    community_id: Optional[UUID] = None


class SurveySubmissionResponse(ORMModel):
    id: UUID
    survey_id: UUID
    survey_version_id: UUID
    version: int
    status: str
    answers: dict
    respondent_name: Optional[str] = None
    created_at: Any


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


@router.get("/surveys", response_model=PaginatedResponse[SurveyResponseModel])
async def list_surveys(
    ctx: Annotated[RequestContext, Depends(require_permissions("surveys:read", "surveys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[SurveyResponseModel]:
    org_id = _require_org(ctx)
    items, total = await survey_service.list_surveys(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[SurveyResponseModel.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/surveys", response_model=SurveyResponseModel, status_code=201)
async def create_survey(
    body: SurveyCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("surveys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyResponseModel:
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
    return SurveyResponseModel.model_validate(row)


@router.get("/surveys/{survey_id}", response_model=dict)
async def get_survey(
    survey_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("surveys:read", "surveys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    survey = await survey_service.get_survey(db, org_id, survey_id)
    version = await survey_service.get_current_version(db, survey)
    return {
        "survey": SurveyResponseModel.model_validate(survey).model_dump(),
        "version": {
            "id": str(version.id),
            "survey_id": str(version.survey_id),
            "version": version.version,
            "title": version.title,
            "schema": version.schema_ or {},
            "published_at": version.published_at,
            "created_at": version.created_at,
        },
    }


@router.patch("/surveys/{survey_id}", response_model=SurveyResponseModel)
async def update_survey(
    survey_id: UUID,
    body: SurveyUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("surveys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveyResponseModel:
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
    return SurveyResponseModel.model_validate(updated)


@router.post(
    "/surveys/{survey_id}/responses",
    response_model=SurveySubmissionResponse,
    status_code=201,
)
async def submit_survey_response(
    survey_id: UUID,
    body: SurveySubmissionRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("surveys:manage", "surveys:read"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurveySubmissionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await survey_service.submit_response(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        survey_id=survey_id,
        answers=body.answers,
        respondent_name=body.respondent_name,
        beneficiary_id=body.beneficiary_id,
        community_id=body.community_id,
        ip_address=ip,
        user_agent=ua,
    )
    return SurveySubmissionResponse.model_validate(row)


@router.get(
    "/survey-responses",
    response_model=PaginatedResponse[SurveySubmissionResponse],
)
async def list_survey_responses(
    ctx: Annotated[RequestContext, Depends(require_permissions("surveys:read", "surveys:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    survey_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SurveySubmissionResponse]:
    org_id = _require_org(ctx)
    items, total = await survey_service.list_responses(
        db, org_id, survey_id=survey_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[SurveySubmissionResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )
