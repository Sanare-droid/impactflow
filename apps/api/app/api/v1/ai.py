from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    AiConversationCreateRequest,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMessageCreateRequest,
    AiMessageResponse,
    AiNarrativeCreateRequest,
    AiNarrativeResponse,
    AiNarrativeUpdateRequest,
    AiPredictionGenerateRequest,
    AiPredictionResponse,
    AiPredictionUpdateRequest,
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.services import ai as ai_service

router = APIRouter(tags=["AI Copilot"])


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


# -------- Copilot --------


@router.get("/ai/conversations", response_model=PaginatedResponse[AiConversationResponse])
async def list_conversations(
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
) -> PaginatedResponse[AiConversationResponse]:
    org_id = _require_org(ctx)
    items, total = await ai_service.list_conversations(
        db, org_id, ctx.user.id, page=page, page_size=page_size, status=status
    )
    return PaginatedResponse(
        items=[AiConversationResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/ai/conversations", response_model=AiConversationResponse, status_code=201)
async def create_conversation(
    body: AiConversationCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    conv = await ai_service.create_conversation(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        title=body.title or "New conversation",
        context=body.context or {},
        ip=ip,
        user_agent=ua,
    )
    return AiConversationResponse.model_validate(conv)


@router.get(
    "/ai/conversations/{conversation_id}",
    response_model=AiConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationDetailResponse:
    org_id = _require_org(ctx)
    conv = await ai_service.get_conversation(db, org_id, ctx.user.id, conversation_id)
    return AiConversationDetailResponse(
        **AiConversationResponse.model_validate(conv).model_dump(),
        messages=[AiMessageResponse.model_validate(m) for m in conv.messages],
    )


@router.post(
    "/ai/conversations/{conversation_id}/messages",
    response_model=AiConversationDetailResponse,
)
async def send_message(
    conversation_id: UUID,
    body: AiMessageCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationDetailResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    conv, _user_msg, _assistant = await ai_service.send_message(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        content=body.content,
        ip=ip,
        user_agent=ua,
    )
    conv = await ai_service.get_conversation(db, org_id, ctx.user.id, conversation_id)
    return AiConversationDetailResponse(
        **AiConversationResponse.model_validate(conv).model_dump(),
        messages=[AiMessageResponse.model_validate(m) for m in conv.messages],
    )


@router.post(
    "/ai/conversations/{conversation_id}/archive",
    response_model=AiConversationResponse,
)
async def archive_conversation(
    conversation_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    conv = await ai_service.archive_conversation(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        ip=ip,
        user_agent=ua,
    )
    return AiConversationResponse.model_validate(conv)


# -------- Predictions --------


@router.get("/ai/predictions", response_model=PaginatedResponse[AiPredictionResponse])
async def list_predictions(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("predictions:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> PaginatedResponse[AiPredictionResponse]:
    org_id = _require_org(ctx)
    items, total = await ai_service.list_predictions(
        db, org_id, page=page, page_size=page_size, status=status, severity=severity
    )
    return PaginatedResponse(
        items=[AiPredictionResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/ai/predictions", response_model=AiPredictionResponse, status_code=201)
async def generate_prediction(
    body: AiPredictionGenerateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("predictions:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiPredictionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    pred = await ai_service.generate_prediction(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        program_id=body.program_id,
        project_id=body.project_id,
        prediction_type=body.prediction_type,
        ip=ip,
        user_agent=ua,
    )
    return AiPredictionResponse.model_validate(pred)


@router.patch("/ai/predictions/{prediction_id}", response_model=AiPredictionResponse)
async def update_prediction(
    prediction_id: UUID,
    body: AiPredictionUpdateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("predictions:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiPredictionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    pred = await ai_service.update_prediction(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        prediction_id=prediction_id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return AiPredictionResponse.model_validate(pred)


# -------- Narratives --------


@router.get("/ai/narratives", response_model=PaginatedResponse[AiNarrativeResponse])
async def list_narratives(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("narratives:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    narrative_type: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[AiNarrativeResponse]:
    org_id = _require_org(ctx)
    items, total = await ai_service.list_narratives(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        narrative_type=narrative_type,
        search=search,
    )
    return PaginatedResponse(
        items=[AiNarrativeResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/ai/narratives", response_model=AiNarrativeResponse, status_code=201)
async def generate_narrative(
    body: AiNarrativeCreateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("narratives:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiNarrativeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ai_service.generate_narrative(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        name=body.name,
        narrative_type=body.narrative_type,
        code=body.code,
        prompt=body.prompt,
        program_id=body.program_id,
        project_id=body.project_id,
        report_id=body.report_id,
        ip=ip,
        user_agent=ua,
    )
    return AiNarrativeResponse.model_validate(row)


@router.patch("/ai/narratives/{narrative_id}", response_model=AiNarrativeResponse)
async def update_narrative(
    narrative_id: UUID,
    body: AiNarrativeUpdateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("narratives:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiNarrativeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ai_service.update_narrative(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        narrative_id=narrative_id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return AiNarrativeResponse.model_validate(row)


@router.delete("/ai/narratives/{narrative_id}", response_model=MessageResponse)
async def delete_narrative(
    narrative_id: UUID,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("narratives:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    await ai_service.delete_narrative(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        narrative_id=narrative_id,
        ip=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Narrative deleted")


# -------- Knowledge --------


@router.get("/knowledge", response_model=PaginatedResponse[KnowledgeResponse])
async def list_knowledge(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("knowledge:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[KnowledgeResponse]:
    org_id = _require_org(ctx)
    items, total = await ai_service.list_knowledge(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        search=search,
    )
    return PaginatedResponse(
        items=[KnowledgeResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/knowledge", response_model=KnowledgeResponse, status_code=201)
async def create_knowledge(
    body: KnowledgeCreateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("knowledge:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ai_service.create_knowledge(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        data=body.model_dump(),
        ip=ip,
        user_agent=ua,
    )
    return KnowledgeResponse.model_validate(row)


@router.get("/knowledge/{document_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    document_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("knowledge:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    org_id = _require_org(ctx)
    row = await ai_service.get_knowledge(db, org_id, document_id)
    return KnowledgeResponse.model_validate(row)


@router.patch("/knowledge/{document_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    document_id: UUID,
    body: KnowledgeUpdateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("knowledge:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    row = await ai_service.update_knowledge(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        document_id=document_id,
        data=body.model_dump(exclude_unset=True),
        ip=ip,
        user_agent=ua,
    )
    return KnowledgeResponse.model_validate(row)


@router.delete("/knowledge/{document_id}", response_model=MessageResponse)
async def delete_knowledge(
    document_id: UUID,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("knowledge:manage", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    await ai_service.delete_knowledge(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        document_id=document_id,
        ip=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Knowledge document deleted")
