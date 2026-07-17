from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.schemas import (
    AiConversationCreateRequest,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiConversationUpdateRequest,
    AiInsightsScanRequest,
    AiMessageCreateRequest,
    AiMessageFeedbackRequest,
    AiMessageResponse,
    AiNarrativeCreateRequest,
    AiNarrativeResponse,
    AiNarrativeUpdateRequest,
    AiPredictionGenerateRequest,
    AiPredictionResponse,
    AiPredictionUpdateRequest,
    AiReportGenerateRequest,
    AiReportResponse,
    AiWorkflowDraftRequest,
    AiWorkflowDraftResponse,
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.services import ai as ai_service
from app.services import ai_orchestrator
from app.services.rate_limit import enforce_rate_limit

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
    pinned: Optional[bool] = None,
) -> PaginatedResponse[AiConversationResponse]:
    org_id = _require_org(ctx)
    items, total = await ai_service.list_conversations(
        db, org_id, ctx.user.id, page=page, page_size=page_size, status=status, pinned=pinned
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
    from app.services import enterprise as ent

    await ent.require_feature(db, org_id, "ai")
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
    await enforce_rate_limit(key=f"rl:ai:msg:{org_id}:{ip}", limit=30, window_seconds=60)
    conv, _user_msg, _assistant = await ai_service.send_message(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        content=body.content,
        permissions=ctx.permissions,
        page_context=body.page_context,
        ip=ip,
        user_agent=ua,
    )
    conv = await ai_service.get_conversation(db, org_id, ctx.user.id, conversation_id)
    return AiConversationDetailResponse(
        **AiConversationResponse.model_validate(conv).model_dump(),
        messages=[AiMessageResponse.model_validate(m) for m in conv.messages],
    )


@router.post("/ai/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    body: AiMessageCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:ai:msg:{org_id}:{ip}", limit=30, window_seconds=60)

    async def _event_source():
        async for event in ai_orchestrator.run_turn_stream(
            db,
            organization_id=org_id,
            user_id=ctx.user.id,
            conversation_id=conversation_id,
            content=body.content,
            permissions=ctx.permissions,
            page_context=body.page_context,
            ip=ip,
            user_agent=ua,
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(_event_source(), media_type="text/event-stream")


@router.patch("/ai/conversations/{conversation_id}", response_model=AiConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    body: AiConversationUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    conv = await ai_service.update_conversation(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        title=body.title,
        pinned=body.pinned,
        ip=ip,
        user_agent=ua,
    )
    return AiConversationResponse.model_validate(conv)


@router.post("/ai/conversations/{conversation_id}/share")
async def share_conversation(
    conversation_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    conv = await ai_service.share_conversation(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        ip=ip,
        user_agent=ua,
    )
    return {
        "share_token": conv.share_token,
        "url_path": f"/app/copilot?share={conv.share_token}",
    }


@router.post("/ai/messages/{message_id}/feedback", response_model=AiMessageResponse)
async def message_feedback(
    message_id: UUID,
    body: AiMessageFeedbackRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiMessageResponse:
    org_id = _require_org(ctx)
    msg = await ai_service.set_message_feedback(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        message_id=message_id,
        feedback=body.feedback,
    )
    return AiMessageResponse.model_validate(msg)


@router.get("/ai/conversations/{conversation_id}/export", response_class=PlainTextResponse)
async def export_conversation(
    conversation_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlainTextResponse:
    org_id = _require_org(ctx)
    conv = await ai_service.get_conversation(db, org_id, ctx.user.id, conversation_id)
    markdown = ai_orchestrator.export_conversation_markdown(conv)
    return PlainTextResponse(markdown, media_type="text/markdown")


@router.post("/ai/conversations/{conversation_id}/regenerate", response_model=AiConversationDetailResponse)
async def regenerate_message(
    conversation_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiConversationDetailResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:ai:msg:{org_id}:{ip}", limit=30, window_seconds=60)
    conv, _user_msg, _assistant, _citations = await ai_orchestrator.regenerate_turn(
        db,
        organization_id=org_id,
        user_id=ctx.user.id,
        conversation_id=conversation_id,
        permissions=ctx.permissions,
        ip=ip,
        user_agent=ua,
    )
    conv = await ai_service.get_conversation(db, org_id, ctx.user.id, conversation_id)
    return AiConversationDetailResponse(
        **AiConversationResponse.model_validate(conv).model_dump(),
        messages=[AiMessageResponse.model_validate(m) for m in conv.messages],
    )


@router.get("/ai/suggested-questions")
async def suggested_questions(
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    questions = await ai_service.suggested_questions(db, org_id)
    return {"questions": questions}


@router.get("/ai/insights/dashboard")
async def dashboard_insights(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("dashboard:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    return await ai_service.dashboard_insights(db, org_id)


@router.post("/ai/insights/scan")
async def scan_insights(
    body: AiInsightsScanRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("predictions:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    return await ai_service.scan_and_persist_predictions(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        persist=body.persist,
        ip=ip,
        user_agent=ua,
    )


@router.post("/ai/reports/generate", response_model=AiReportResponse)
async def generate_report(
    body: AiReportGenerateRequest,
    request: Request,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("reports:read", "ai:use"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiReportResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:ai:report:{org_id}:{ip}", limit=20, window_seconds=60)
    report = await ai_service.generate_report(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        report_type=body.report_type,
        program_id=body.program_id,
        project_id=body.project_id,
        permissions=ctx.permissions,
        save_narrative=body.save_narrative,
        ip=ip,
        user_agent=ua,
    )
    return AiReportResponse(
        report_type=report["report_type"],
        title=report["title"],
        content=report["content"],
        provider=report["provider"],
        model=report.get("model"),
        generated_at=report["generated_at"],
        narrative_id=report.get("narrative_id"),
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


# -------- Workflow drafting --------


@router.post("/ai/workflows/draft", response_model=AiWorkflowDraftResponse)
async def draft_workflow(
    body: AiWorkflowDraftRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("ai:use"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiWorkflowDraftResponse:
    org_id = _require_org(ctx)
    if body.save and not ctx.has_permission("workflows:manage"):
        raise ForbiddenError(
            "Saving a drafted workflow requires workflows:manage",
            details={"required": ["workflows:manage"]},
        )
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:ai:wf:{org_id}:{ip}", limit=20, window_seconds=60)
    result = await ai_service.draft_workflow(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        prompt=body.prompt,
        page_context=body.page_context,
        save=body.save,
        ip=ip,
        user_agent=ua,
    )
    return AiWorkflowDraftResponse(**result)


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
    await enforce_rate_limit(key=f"rl:ai:pred:{org_id}:{ip}", limit=20, window_seconds=60)
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
    await enforce_rate_limit(key=f"rl:ai:nar:{org_id}:{ip}", limit=20, window_seconds=60)
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
