from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    EvaluationCreateRequest,
    EvaluationResponse,
    EvaluationUpdateRequest,
    IndicatorCreateRequest,
    IndicatorResponse,
    IndicatorTargetCreateRequest,
    IndicatorTargetResponse,
    IndicatorUpdateRequest,
    LogframeCreateRequest,
    LogframeResponse,
    LogframeResultCreateRequest,
    LogframeResultResponse,
    LogframeUpdateRequest,
    MessageResponse,
    MonitoringResultCreateRequest,
    MonitoringResultResponse,
    MonitoringResultUpdateRequest,
    PaginatedResponse,
    PaginationMeta,
    TheoryOfChangeCreateRequest,
    TheoryOfChangeResponse,
    TheoryOfChangeUpdateRequest,
)
from app.services import meal as meal_service

router = APIRouter(tags=["MEAL"])


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


# -------- Theory of Change --------


@router.get("/theories-of-change", response_model=PaginatedResponse[TheoryOfChangeResponse])
async def list_tocs(
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("theories_of_change:read", "theories_of_change:manage")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[TheoryOfChangeResponse]:
    org_id = _require_org(ctx)
    items, total = await meal_service.list_tocs(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[TheoryOfChangeResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/theories-of-change", response_model=TheoryOfChangeResponse, status_code=201)
async def create_toc(
    body: TheoryOfChangeCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("theories_of_change:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TheoryOfChangeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    toc = await meal_service.create_toc(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return TheoryOfChangeResponse.model_validate(toc)


@router.get("/theories-of-change/{toc_id}", response_model=TheoryOfChangeResponse)
async def get_toc(
    toc_id: UUID,
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("theories_of_change:read", "theories_of_change:manage")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TheoryOfChangeResponse:
    org_id = _require_org(ctx)
    toc = await meal_service.get_toc(db, org_id, toc_id)
    return TheoryOfChangeResponse.model_validate(toc)


@router.patch("/theories-of-change/{toc_id}", response_model=TheoryOfChangeResponse)
async def update_toc(
    toc_id: UUID,
    body: TheoryOfChangeUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("theories_of_change:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TheoryOfChangeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    toc = await meal_service.get_toc(db, org_id, toc_id)
    updated = await meal_service.update_toc(
        db,
        toc,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return TheoryOfChangeResponse.model_validate(updated)


@router.delete("/theories-of-change/{toc_id}", response_model=MessageResponse)
async def delete_toc(
    toc_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("theories_of_change:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    toc = await meal_service.get_toc(db, org_id, toc_id)
    await meal_service.delete_toc(
        db,
        toc,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Theory of Change deleted")


# -------- Logframes --------


@router.get("/logframes", response_model=PaginatedResponse[LogframeResponse])
async def list_logframes(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("logframes:read", "logframes:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[LogframeResponse]:
    org_id = _require_org(ctx)
    items, total = await meal_service.list_logframes(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[LogframeResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/logframes", response_model=LogframeResponse, status_code=201)
async def create_logframe(
    body: LogframeCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("logframes:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LogframeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    logframe = await meal_service.create_logframe(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return LogframeResponse.model_validate(logframe)


@router.get("/logframes/{logframe_id}", response_model=LogframeResponse)
async def get_logframe(
    logframe_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("logframes:read", "logframes:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LogframeResponse:
    org_id = _require_org(ctx)
    logframe = await meal_service.get_logframe(db, org_id, logframe_id)
    return LogframeResponse.model_validate(logframe)


@router.patch("/logframes/{logframe_id}", response_model=LogframeResponse)
async def update_logframe(
    logframe_id: UUID,
    body: LogframeUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("logframes:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LogframeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    logframe = await meal_service.get_logframe(db, org_id, logframe_id)
    updated = await meal_service.update_logframe(
        db,
        logframe,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return LogframeResponse.model_validate(updated)


@router.delete("/logframes/{logframe_id}", response_model=MessageResponse)
async def delete_logframe(
    logframe_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("logframes:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    logframe = await meal_service.get_logframe(db, org_id, logframe_id)
    await meal_service.delete_logframe(
        db,
        logframe,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Logframe deleted")


@router.post(
    "/logframes/{logframe_id}/results",
    response_model=LogframeResultResponse,
    status_code=201,
)
async def add_logframe_result(
    logframe_id: UUID,
    body: LogframeResultCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("logframes:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LogframeResultResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    logframe = await meal_service.get_logframe(db, org_id, logframe_id)
    result = await meal_service.add_logframe_result(
        db,
        logframe,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return LogframeResultResponse.model_validate(result)


# -------- Indicators --------


@router.get("/indicators/progress")
async def indicators_progress(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("indicators:read", "indicators:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    items = await meal_service.indicator_progress(db, org_id)
    return {"items": items}


@router.get("/indicators", response_model=PaginatedResponse[IndicatorResponse])
async def list_indicators(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("indicators:read", "indicators:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[IndicatorResponse]:
    org_id = _require_org(ctx)
    items, total = await meal_service.list_indicators(
        db, org_id, page=page, page_size=page_size, status=status, level=level, search=search
    )
    return PaginatedResponse(
        items=[IndicatorResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/indicators", response_model=IndicatorResponse, status_code=201)
async def create_indicator(
    body: IndicatorCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("indicators:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndicatorResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    indicator = await meal_service.create_indicator(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return IndicatorResponse.model_validate(indicator)


@router.get("/indicators/{indicator_id}", response_model=IndicatorResponse)
async def get_indicator(
    indicator_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("indicators:read", "indicators:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndicatorResponse:
    org_id = _require_org(ctx)
    indicator = await meal_service.get_indicator(db, org_id, indicator_id)
    return IndicatorResponse.model_validate(indicator)


@router.patch("/indicators/{indicator_id}", response_model=IndicatorResponse)
async def update_indicator(
    indicator_id: UUID,
    body: IndicatorUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("indicators:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndicatorResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    indicator = await meal_service.get_indicator(db, org_id, indicator_id)
    updated = await meal_service.update_indicator(
        db,
        indicator,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return IndicatorResponse.model_validate(updated)


@router.delete("/indicators/{indicator_id}", response_model=MessageResponse)
async def delete_indicator(
    indicator_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("indicators:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    indicator = await meal_service.get_indicator(db, org_id, indicator_id)
    await meal_service.delete_indicator(
        db,
        indicator,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Indicator deleted")


@router.post(
    "/indicators/{indicator_id}/targets",
    response_model=IndicatorTargetResponse,
    status_code=201,
)
async def add_indicator_target(
    indicator_id: UUID,
    body: IndicatorTargetCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("indicators:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndicatorTargetResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    indicator = await meal_service.get_indicator(db, org_id, indicator_id)
    target = await meal_service.add_indicator_target(
        db,
        indicator,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return IndicatorTargetResponse.model_validate(target)


# -------- Monitoring --------


@router.get("/monitoring-results", response_model=PaginatedResponse[MonitoringResultResponse])
async def list_monitoring_results(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("monitoring:read", "monitoring:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    indicator_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> PaginatedResponse[MonitoringResultResponse]:
    org_id = _require_org(ctx)
    items, total = await meal_service.list_monitoring_results(
        db,
        org_id,
        page=page,
        page_size=page_size,
        indicator_id=indicator_id,
        status=status,
    )
    return PaginatedResponse(
        items=[MonitoringResultResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/monitoring-results", response_model=MonitoringResultResponse, status_code=201)
async def create_monitoring_result(
    body: MonitoringResultCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("monitoring:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitoringResultResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    result = await meal_service.create_monitoring_result(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return MonitoringResultResponse.model_validate(result)


@router.patch("/monitoring-results/{result_id}", response_model=MonitoringResultResponse)
async def update_monitoring_result(
    result_id: UUID,
    body: MonitoringResultUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("monitoring:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitoringResultResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    result = await meal_service.get_monitoring_result(db, org_id, result_id)
    updated = await meal_service.update_monitoring_result(
        db,
        result,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return MonitoringResultResponse.model_validate(updated)


@router.delete("/monitoring-results/{result_id}", response_model=MessageResponse)
async def delete_monitoring_result(
    result_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("monitoring:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    result = await meal_service.get_monitoring_result(db, org_id, result_id)
    await meal_service.delete_monitoring_result(
        db,
        result,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Monitoring result deleted")


# -------- Evaluations --------


@router.get("/evaluations", response_model=PaginatedResponse[EvaluationResponse])
async def list_evaluations(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("evaluations:read", "evaluations:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    evaluation_type: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[EvaluationResponse]:
    org_id = _require_org(ctx)
    items, total = await meal_service.list_evaluations(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        evaluation_type=evaluation_type,
        search=search,
    )
    return PaginatedResponse(
        items=[EvaluationResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/evaluations", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(
    body: EvaluationCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evaluations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    evaluation = await meal_service.create_evaluation(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return EvaluationResponse.model_validate(evaluation)


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("evaluations:read", "evaluations:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationResponse:
    org_id = _require_org(ctx)
    evaluation = await meal_service.get_evaluation(db, org_id, evaluation_id)
    return EvaluationResponse.model_validate(evaluation)


@router.patch("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def update_evaluation(
    evaluation_id: UUID,
    body: EvaluationUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evaluations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    evaluation = await meal_service.get_evaluation(db, org_id, evaluation_id)
    updated = await meal_service.update_evaluation(
        db,
        evaluation,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return EvaluationResponse.model_validate(updated)


@router.delete("/evaluations/{evaluation_id}", response_model=MessageResponse)
async def delete_evaluation(
    evaluation_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("evaluations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    evaluation = await meal_service.get_evaluation(db, org_id, evaluation_id)
    await meal_service.delete_evaluation(
        db,
        evaluation,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Evaluation deleted")
