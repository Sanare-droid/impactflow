from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.ai import AiConversation, AiMessage
from app.models.knowledge import KnowledgeDocument
from app.models.narrative import AiNarrative
from app.models.prediction import AiPrediction
from app.models.program import Program
from app.models.project import Project
from app.models.report import Report
from app.services import ai_provider
from app.services.audit import write_audit_log
from app.services.beneficiaries import phase5_counts
from app.services.finance import phase3_counts
from app.services.insights import phase6_counts
from app.services.meal import phase4_counts
from app.services.programs import _ensure_unique_code, make_code, phase2_counts


def _dec(value: Optional[Decimal | float | int | str]) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


async def _assert_program(db: AsyncSession, organization_id: UUID, program_id: UUID) -> None:
    exists = await db.scalar(
        select(Program.id).where(Program.id == program_id, Program.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Program not found")


async def _assert_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> None:
    exists = await db.scalar(
        select(Project.id).where(Project.id == project_id, Project.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Project not found")


async def _assert_report(db: AsyncSession, organization_id: UUID, report_id: UUID) -> None:
    exists = await db.scalar(
        select(Report.id).where(Report.id == report_id, Report.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Report not found")


async def _org_snapshot(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    snapshot.update(await phase2_counts(db, organization_id))
    snapshot.update(await phase3_counts(db, organization_id))
    snapshot.update(await phase4_counts(db, organization_id))
    snapshot.update(await phase5_counts(db, organization_id))
    snapshot.update(await phase6_counts(db, organization_id))
    return snapshot


async def phase7_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    conversations = await db.scalar(
        select(func.count())
        .select_from(AiConversation)
        .where(AiConversation.organization_id == organization_id)
    )
    predictions = await db.scalar(
        select(func.count())
        .select_from(AiPrediction)
        .where(AiPrediction.organization_id == organization_id)
    )
    open_predictions = await db.scalar(
        select(func.count())
        .select_from(AiPrediction)
        .where(
            AiPrediction.organization_id == organization_id,
            AiPrediction.status == "open",
        )
    )
    narratives = await db.scalar(
        select(func.count())
        .select_from(AiNarrative)
        .where(AiNarrative.organization_id == organization_id)
    )
    knowledge = await db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(KnowledgeDocument.organization_id == organization_id)
    )
    return {
        "ai_conversations_count": conversations or 0,
        "ai_predictions_count": predictions or 0,
        "open_predictions_count": open_predictions or 0,
        "ai_narratives_count": narratives or 0,
        "knowledge_documents_count": knowledge or 0,
    }


# -------- Copilot --------


async def list_conversations(
    db: AsyncSession,
    organization_id: UUID,
    user_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> tuple[list[AiConversation], int]:
    filters = [
        AiConversation.organization_id == organization_id,
        AiConversation.user_id == user_id,
    ]
    if status:
        filters.append(AiConversation.status == status)
    total = await db.scalar(select(func.count()).select_from(AiConversation).where(*filters))
    result = await db.scalars(
        select(AiConversation)
        .where(*filters)
        .order_by(AiConversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), total or 0


async def get_conversation(
    db: AsyncSession, organization_id: UUID, user_id: UUID, conversation_id: UUID
) -> AiConversation:
    conv = await db.scalar(
        select(AiConversation)
        .options(selectinload(AiConversation.messages))
        .where(
            AiConversation.id == conversation_id,
            AiConversation.organization_id == organization_id,
            AiConversation.user_id == user_id,
        )
    )
    if not conv:
        raise NotFoundError("Conversation not found")
    return conv


async def create_conversation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    title: str = "New conversation",
    context: Optional[dict] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiConversation:
    conv = AiConversation(
        organization_id=organization_id,
        user_id=user_id,
        title=title[:255],
        context=context or {},
    )
    db.add(conv)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=user_id,
        action="ai.conversation.create",
        resource_type="ai_conversation",
        resource_id=str(conv.id),
        description=f"Created AI conversation '{conv.title}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.refresh(conv)
    return conv


async def send_message(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[AiConversation, AiMessage, AiMessage]:
    conv = await get_conversation(db, organization_id, user_id, conversation_id)
    user_msg = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="user",
        content=content,
        provider="user",
    )
    db.add(user_msg)
    await db.flush()

    # Ground with knowledge snippets + org snapshot
    knowledge_hits = await search_knowledge(db, organization_id, query=content, limit=3)
    snapshot = await _org_snapshot(db, organization_id)
    knowledge_block = "\n\n".join(
        f"[{d.code}] {d.name}: {(d.summary or d.content)[:400]}" for d in knowledge_hits
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
        if m.role in ("user", "assistant")
    ]
    history.append({"role": "user", "content": content})
    system = (
        ai_provider.SYSTEM_PROMPT
        + f"\n\nOrganization snapshot: {snapshot}"
        + (f"\n\nRelevant knowledge:\n{knowledge_block}" if knowledge_block else "")
    )
    result = await ai_provider.chat_completion(history, system=system)
    assistant = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="assistant",
        content=result["content"],
        provider=result["provider"],
        model=result.get("model"),
        token_count=result.get("token_count"),
        metadata_={"knowledge_ids": [str(d.id) for d in knowledge_hits]},
    )
    db.add(assistant)
    if conv.title == "New conversation" and content.strip():
        conv.title = content.strip()[:80]
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=user_id,
        action="ai.conversation.message",
        resource_type="ai_conversation",
        resource_id=str(conv.id),
        description="Sent AI copilot message",
        ip_address=ip,
        user_agent=user_agent,
        changes={"provider": result["provider"]},
    )
    await db.refresh(conv)
    await db.refresh(user_msg)
    await db.refresh(assistant)
    return conv, user_msg, assistant


async def archive_conversation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiConversation:
    conv = await get_conversation(db, organization_id, user_id, conversation_id)
    conv.status = "archived"
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=user_id,
        action="ai.conversation.archive",
        resource_type="ai_conversation",
        resource_id=str(conv.id),
        description=f"Archived AI conversation '{conv.title}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.refresh(conv)
    return conv


# -------- Predictions --------


async def list_predictions(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> tuple[list[AiPrediction], int]:
    filters = [AiPrediction.organization_id == organization_id]
    if status:
        filters.append(AiPrediction.status == status)
    if severity:
        filters.append(AiPrediction.severity == severity)
    total = await db.scalar(select(func.count()).select_from(AiPrediction).where(*filters))
    result = await db.scalars(
        select(AiPrediction)
        .where(*filters)
        .order_by(AiPrediction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), total or 0


async def get_prediction(
    db: AsyncSession, organization_id: UUID, prediction_id: UUID
) -> AiPrediction:
    row = await db.scalar(
        select(AiPrediction).where(
            AiPrediction.id == prediction_id,
            AiPrediction.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Prediction not found")
    return row


async def generate_prediction(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    prediction_type: str = "project_risk",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiPrediction:
    if program_id:
        await _assert_program(db, organization_id, program_id)
    if project_id:
        await _assert_project(db, organization_id, project_id)
    snapshot = await _org_snapshot(db, organization_id)
    snapshot["prediction_type"] = prediction_type
    if program_id:
        snapshot["program_id"] = str(program_id)
    if project_id:
        snapshot["project_id"] = str(project_id)
    generated = await ai_provider.generate_prediction_text(snapshot)
    pred = AiPrediction(
        organization_id=organization_id,
        program_id=program_id,
        project_id=project_id,
        prediction_type=prediction_type,
        title=str(generated.get("title") or "Risk prediction")[:255],
        summary=str(generated.get("summary") or "No summary"),
        severity=str(generated.get("severity") or "medium"),
        score=_dec(generated.get("score") or 50),
        recommendations=list(generated.get("recommendations") or []),
        signals=snapshot,
        provider=str(generated.get("provider") or ai_provider.provider_name()),
        model=generated.get("model"),
        created_by_id=actor_id,
    )
    db.add(pred)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="ai.prediction.create",
        resource_type="ai_prediction",
        resource_id=str(pred.id),
        description=f"Generated prediction '{pred.title}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={"severity": pred.severity, "provider": pred.provider},
    )
    await db.refresh(pred)
    return pred


async def update_prediction(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    prediction_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiPrediction:
    pred = await get_prediction(db, organization_id, prediction_id)
    for key, value in data.items():
        if value is not None and hasattr(pred, key):
            setattr(pred, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="ai.prediction.update",
        resource_type="ai_prediction",
        resource_id=str(pred.id),
        description=f"Updated prediction '{pred.title}'",
        ip_address=ip,
        user_agent=user_agent,
        changes=data,
    )
    await db.refresh(pred)
    return pred


# -------- Narratives --------


async def list_narratives(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    narrative_type: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[AiNarrative], int]:
    filters = [AiNarrative.organization_id == organization_id]
    if status:
        filters.append(AiNarrative.status == status)
    if narrative_type:
        filters.append(AiNarrative.narrative_type == narrative_type)
    if search:
        like = f"%{search}%"
        filters.append(or_(AiNarrative.name.ilike(like), AiNarrative.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(AiNarrative).where(*filters))
    result = await db.scalars(
        select(AiNarrative)
        .where(*filters)
        .order_by(AiNarrative.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), total or 0


async def get_narrative(
    db: AsyncSession, organization_id: UUID, narrative_id: UUID
) -> AiNarrative:
    row = await db.scalar(
        select(AiNarrative).where(
            AiNarrative.id == narrative_id,
            AiNarrative.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Narrative not found")
    return row


async def generate_narrative(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    name: str,
    narrative_type: str = "executive_summary",
    code: Optional[str] = None,
    prompt: Optional[str] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    report_id: Optional[UUID] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiNarrative:
    if program_id:
        await _assert_program(db, organization_id, program_id)
    if project_id:
        await _assert_project(db, organization_id, project_id)
    if report_id:
        await _assert_report(db, organization_id, report_id)
    snapshot = await _org_snapshot(db, organization_id)
    generated = await ai_provider.generate_narrative_text(
        narrative_type, snapshot, prompt=prompt
    )
    unique_code = await _ensure_unique_code(
        db,
        model=AiNarrative,
        organization_id=organization_id,
        code=make_code(code or name, prefix="NAR-"),
    )
    row = AiNarrative(
        organization_id=organization_id,
        program_id=program_id,
        project_id=project_id,
        report_id=report_id,
        name=name,
        code=unique_code,
        narrative_type=narrative_type,
        prompt=prompt,
        content=generated["content"],
        provider=generated["provider"],
        model=generated.get("model"),
        created_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="ai.narrative.create",
        resource_type="ai_narrative",
        resource_id=str(row.id),
        description=f"Generated narrative '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes={"provider": row.provider, "type": narrative_type},
    )
    await db.refresh(row)
    return row


async def update_narrative(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    narrative_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AiNarrative:
    row = await get_narrative(db, organization_id, narrative_id)
    if "code" in data and data["code"] and data["code"] != row.code:
        data["code"] = await _ensure_unique_code(
            db,
            model=AiNarrative,
            organization_id=organization_id,
            code=make_code(data["code"], prefix="NAR-"),
        )
    for key, value in data.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="ai.narrative.update",
        resource_type="ai_narrative",
        resource_id=str(row.id),
        description=f"Updated narrative '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes=data,
    )
    await db.refresh(row)
    return row


async def delete_narrative(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    narrative_id: UUID,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    row = await get_narrative(db, organization_id, narrative_id)
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="ai.narrative.delete",
        resource_type="ai_narrative",
        resource_id=str(row.id),
        description=f"Deleted narrative '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.delete(row)


# -------- Knowledge --------


async def list_knowledge(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[KnowledgeDocument], int]:
    filters = [KnowledgeDocument.organization_id == organization_id]
    if status:
        filters.append(KnowledgeDocument.status == status)
    if category:
        filters.append(KnowledgeDocument.category == category)
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                KnowledgeDocument.name.ilike(like),
                KnowledgeDocument.code.ilike(like),
                KnowledgeDocument.content.ilike(like),
                KnowledgeDocument.summary.ilike(like),
            )
        )
    total = await db.scalar(select(func.count()).select_from(KnowledgeDocument).where(*filters))
    result = await db.scalars(
        select(KnowledgeDocument)
        .where(*filters)
        .order_by(KnowledgeDocument.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), total or 0


async def search_knowledge(
    db: AsyncSession,
    organization_id: UUID,
    *,
    query: str,
    limit: int = 5,
) -> list[KnowledgeDocument]:
    like = f"%{query.strip()[:80]}%"
    if not query.strip():
        return []
    result = await db.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.status == "published",
            or_(
                KnowledgeDocument.name.ilike(like),
                KnowledgeDocument.content.ilike(like),
                KnowledgeDocument.summary.ilike(like),
            ),
        )
        .order_by(KnowledgeDocument.updated_at.desc())
        .limit(limit)
    )
    return list(result)


async def get_knowledge(
    db: AsyncSession, organization_id: UUID, document_id: UUID
) -> KnowledgeDocument:
    row = await db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Knowledge document not found")
    return row


async def create_knowledge(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> KnowledgeDocument:
    code = await _ensure_unique_code(
        db,
        model=KnowledgeDocument,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="KB-"),
    )
    row = KnowledgeDocument(
        organization_id=organization_id,
        name=data["name"],
        code=code,
        category=data.get("category") or "guidance",
        status=data.get("status") or "published",
        summary=data.get("summary"),
        content=data["content"],
        source=data.get("source"),
        tags=data.get("tags") or [],
        metadata_=data.get("metadata") or {},
        created_by_id=actor_id,
    )
    db.add(row)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="knowledge.create",
        resource_type="knowledge_document",
        resource_id=str(row.id),
        description=f"Created knowledge document '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.refresh(row)
    return row


async def update_knowledge(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    document_id: UUID,
    data: dict,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> KnowledgeDocument:
    row = await get_knowledge(db, organization_id, document_id)
    if "code" in data and data["code"] and data["code"] != row.code:
        data["code"] = await _ensure_unique_code(
            db,
            model=KnowledgeDocument,
            organization_id=organization_id,
            code=make_code(data["code"], prefix="KB-"),
        )
    for key, value in data.items():
        if key == "metadata" and value is not None:
            row.metadata_ = value
        elif value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="knowledge.update",
        resource_type="knowledge_document",
        resource_id=str(row.id),
        description=f"Updated knowledge document '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
        changes=data,
    )
    await db.refresh(row)
    return row


async def delete_knowledge(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    document_id: UUID,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    row = await get_knowledge(db, organization_id, document_id)
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="knowledge.delete",
        resource_type="knowledge_document",
        resource_id=str(row.id),
        description=f"Deleted knowledge document '{row.name}'",
        ip_address=ip,
        user_agent=user_agent,
    )
    await db.delete(row)
