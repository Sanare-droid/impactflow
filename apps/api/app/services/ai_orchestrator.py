"""AI Copilot orchestration: grounded, tool-augmented chat turns.

This module owns the business logic for a copilot turn. Routers stay thin and
call :func:`run_turn` (or :func:`run_turn_stream`). It reuses the existing
``AiConversation`` / ``AiMessage`` tables and the single ``ai_provider`` LLM
client — no parallel infrastructure.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AiConversation, AiMessage, AiRequestLog
from app.services import ai_provider, ai_tools

SYSTEM_GROUNDED = (
    "You are ImpactFlow AI, an enterprise MEAL and grants copilot for NGOs. "
    "You must be strictly grounded: NEVER invent numbers, names, or facts. "
    "Only use the data provided in the TOOL DATA and KNOWLEDGE sections below. "
    "When you state a figure or name, cite its source inline as [type:label] "
    "(for example [indicator:Children vaccinated] or [grant:GAVI 2026]). "
    "If the provided data is insufficient to answer, say so plainly and suggest "
    "what the user should collect or open next. Be concise and action-oriented. "
    "Never reveal donor or beneficiary PII beyond what the tool data already contains."
)

_KNOWLEDGE_LIMIT = 4


def _build_history(conv: AiConversation) -> list[dict[str, str]]:
    return [
        {"role": m.role, "content": m.content}
        for m in conv.messages
        if m.role in ("user", "assistant")
    ]


def _build_system_prompt(
    *,
    tool_results: dict[str, Any],
    knowledge_block: str,
    page_context: Optional[dict[str, Any]],
    permissions: list[str] | set[str],
) -> str:
    tool_json = json.dumps(tool_results, default=str)[:12000]
    sections = [SYSTEM_GROUNDED, "", "TOOL DATA (authoritative, live from this org):", tool_json]
    if knowledge_block:
        sections += ["", "KNOWLEDGE (published org documents):", knowledge_block]
    if page_context:
        sections += ["", "PAGE CONTEXT (what the user is viewing):", json.dumps(page_context, default=str)[:2000]]
    perm_note = "read-only" if permissions else "limited"
    sections += [
        "",
        f"USER PERMISSIONS NOTE: the user has {perm_note} access to the modules above; "
        "do not reference data outside the provided tool results.",
    ]
    return "\n".join(sections)


async def _gather_grounding(
    db: AsyncSession,
    organization_id: UUID,
    content: str,
    permissions: list[str] | set[str],
) -> tuple[dict[str, Any], list, str]:
    """Run selected tools + knowledge search. Returns (tool_run, knowledge_hits, knowledge_block)."""
    from app.services import ai as ai_service

    tool_names = ai_tools.select_tools(content)
    tool_run = await ai_tools.run_tools(
        db, organization_id, tool_names, content, permissions
    )

    knowledge_hits = await ai_service.search_knowledge(
        db, organization_id, query=content, limit=_KNOWLEDGE_LIMIT
    )
    knowledge_block = "\n\n".join(
        f"[knowledge:{d.name}] {(d.summary or d.content or '')[:400]}" for d in knowledge_hits
    )
    return tool_run, knowledge_hits, knowledge_block


async def run_turn(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    permissions: list[str] | set[str],
    page_context: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[AiConversation, AiMessage, AiMessage, list[dict[str, Any]]]:
    """Execute one grounded copilot turn and persist both messages."""
    from app.services import ai as ai_service
    from app.services.audit import write_audit_log

    started = time.perf_counter()
    conv = await ai_service.get_conversation(db, organization_id, user_id, conversation_id)

    user_msg = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="user",
        content=content,
        provider="user",
    )
    db.add(user_msg)
    await db.flush()

    tool_run, knowledge_hits, knowledge_block = await _gather_grounding(
        db, organization_id, content, permissions
    )
    knowledge_ids = [str(d.id) for d in knowledge_hits]
    knowledge_citations = [
        {"type": "knowledge", "id": str(d.id), "label": d.name} for d in knowledge_hits
    ]

    system = _build_system_prompt(
        tool_results=tool_run["results"],
        knowledge_block=knowledge_block,
        page_context=page_context,
        permissions=permissions,
    )

    history = _build_history(conv)
    history.append({"role": "user", "content": content})

    success = True
    error_code: Optional[str] = None
    try:
        result = await ai_provider.chat_completion(
            history, system=system, grounding=tool_run
        )
    except Exception as exc:  # noqa: BLE001
        success = False
        error_code = type(exc).__name__
        result = {
            "content": "I could not complete this request right now. Please try again.",
            "provider": ai_provider.provider_name(),
            "model": None,
            "token_count": None,
        }

    citations = list(tool_run["citations"])
    for cite in knowledge_citations:
        if cite not in citations:
            citations.append(cite)

    assistant = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="assistant",
        content=result["content"],
        provider=result["provider"],
        model=result.get("model"),
        token_count=result.get("token_count"),
        metadata_={
            "citations": citations,
            "tools_used": tool_run["tools_used"],
            "knowledge_ids": knowledge_ids,
            "page_context": page_context or {},
        },
    )
    db.add(assistant)

    if conv.title == "New conversation" and content.strip():
        conv.title = content.strip()[:80]

    await db.flush()

    duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        AiRequestLog(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conv.id,
            action="chat",
            tools_used=tool_run["tools_used"],
            model=result.get("model"),
            provider=result["provider"],
            token_count=result.get("token_count"),
            duration_ms=duration_ms,
            success=success,
            prompt_preview=content[:500],
            error_code=error_code,
            metadata_={
                "citation_count": len(citations),
                "knowledge_ids": knowledge_ids,
            },
        )
    )

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
        changes={"provider": result["provider"], "tools_used": tool_run["tools_used"]},
    )

    await db.flush()
    await db.refresh(conv)
    await db.refresh(user_msg)
    await db.refresh(assistant)
    return conv, user_msg, assistant, citations


async def run_turn_stream(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    permissions: list[str] | set[str],
    page_context: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream a copilot turn as event dicts.

    Yields events shaped like ``{"event": tool_start|tool_result|token|done|error, ...}``.
    Both messages are persisted before the terminal ``done`` event.
    """
    from app.services import ai as ai_service
    from app.services.audit import write_audit_log

    started = time.perf_counter()
    try:
        conv = await ai_service.get_conversation(db, organization_id, user_id, conversation_id)
    except Exception as exc:  # noqa: BLE001
        yield {"event": "error", "error": "conversation_not_found", "detail": str(exc)[:200]}
        return

    user_msg = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="user",
        content=content,
        provider="user",
    )
    db.add(user_msg)
    await db.flush()

    tool_names = ai_tools.select_tools(content)
    from app.services import ai as _ai

    tool_run: dict[str, Any] = {"results": {}, "citations": [], "tools_used": []}
    for name in tool_names:
        yield {"event": "tool_start", "tool": name}
        single = await ai_tools.run_tools(
            db, organization_id, [name], content, permissions
        )
        tool_run["results"].update(single["results"])
        for cite in single["citations"]:
            if cite not in tool_run["citations"]:
                tool_run["citations"].append(cite)
        tool_run["tools_used"].extend(single["tools_used"])
        yield {"event": "tool_result", "tool": name, "ok": name in single["tools_used"]}

    knowledge_hits = await _ai.search_knowledge(
        db, organization_id, query=content, limit=_KNOWLEDGE_LIMIT
    )
    knowledge_ids = [str(d.id) for d in knowledge_hits]
    knowledge_block = "\n\n".join(
        f"[knowledge:{d.name}] {(d.summary or d.content or '')[:400]}" for d in knowledge_hits
    )
    citations = list(tool_run["citations"])
    for d in knowledge_hits:
        cite = {"type": "knowledge", "id": str(d.id), "label": d.name}
        if cite not in citations:
            citations.append(cite)

    system = _build_system_prompt(
        tool_results=tool_run["results"],
        knowledge_block=knowledge_block,
        page_context=page_context,
        permissions=permissions,
    )
    history = _build_history(conv)
    history.append({"role": "user", "content": content})

    chunks: list[str] = []
    success = True
    error_code: Optional[str] = None
    try:
        async for token in ai_provider.chat_completion_stream(
            history, system=system, grounding=tool_run
        ):
            chunks.append(token)
            yield {"event": "token", "text": token}
    except Exception as exc:  # noqa: BLE001
        success = False
        error_code = type(exc).__name__
        yield {"event": "error", "error": "generation_failed", "detail": str(exc)[:200]}

    full_content = "".join(chunks) or "(no content)"
    provider = ai_provider.provider_name()

    assistant = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="assistant",
        content=full_content,
        provider=provider,
        model=None,
        metadata_={
            "citations": citations,
            "tools_used": tool_run["tools_used"],
            "knowledge_ids": knowledge_ids,
            "page_context": page_context or {},
        },
    )
    db.add(assistant)
    if conv.title == "New conversation" and content.strip():
        conv.title = content.strip()[:80]
    await db.flush()

    duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        AiRequestLog(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conv.id,
            action="chat",
            tools_used=tool_run["tools_used"],
            model=None,
            provider=provider,
            token_count=None,
            duration_ms=duration_ms,
            success=success,
            prompt_preview=content[:500],
            error_code=error_code,
            metadata_={"citation_count": len(citations), "streamed": True},
        )
    )
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=user_id,
        action="ai.conversation.message",
        resource_type="ai_conversation",
        resource_id=str(conv.id),
        description="Sent AI copilot message (stream)",
        ip_address=ip,
        user_agent=user_agent,
        changes={"provider": provider, "tools_used": tool_run["tools_used"]},
    )
    await db.flush()

    yield {
        "event": "done",
        "conversation_id": str(conv.id),
        "message_id": str(assistant.id),
        "citations": citations,
        "tools_used": tool_run["tools_used"],
    }


async def regenerate_turn(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    permissions: list[str] | set[str],
    page_context: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[AiConversation, AiMessage, AiMessage, list[dict[str, Any]]]:
    """Re-answer the last user message without duplicating it.

    Deletes any assistant messages after the last user turn, then runs a fresh
    grounded generation for that same user content.
    """
    from app.services import ai as ai_service
    from app.services.audit import write_audit_log

    started = time.perf_counter()
    conv = await ai_service.get_conversation(db, organization_id, user_id, conversation_id)
    messages = list(conv.messages)
    last_user = next((m for m in reversed(messages) if m.role == "user"), None)
    if not last_user:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("No user message to regenerate")

    # Drop trailing assistant replies after the last user message
    for m in messages:
        if m.created_at >= last_user.created_at and m.role == "assistant":
            await db.delete(m)
    await db.flush()

    # Reload conversation without the deleted assistants
    conv = await ai_service.get_conversation(db, organization_id, user_id, conversation_id)
    content = last_user.content

    tool_run, knowledge_hits, knowledge_block = await _gather_grounding(
        db, organization_id, content, permissions
    )
    knowledge_ids = [str(d.id) for d in knowledge_hits]
    knowledge_citations = [
        {"type": "knowledge", "id": str(d.id), "label": d.name} for d in knowledge_hits
    ]

    system = _build_system_prompt(
        tool_results=tool_run["results"],
        knowledge_block=knowledge_block,
        page_context=page_context,
        permissions=permissions,
    )
    history = _build_history(conv)

    success = True
    error_code: Optional[str] = None
    try:
        result = await ai_provider.chat_completion(
            history, system=system, grounding=tool_run
        )
    except Exception as exc:  # noqa: BLE001
        success = False
        error_code = type(exc).__name__
        result = {
            "content": "I could not complete this request right now. Please try again.",
            "provider": ai_provider.provider_name(),
            "model": None,
            "token_count": None,
        }

    citations = list(tool_run["citations"])
    for cite in knowledge_citations:
        if cite not in citations:
            citations.append(cite)

    assistant = AiMessage(
        organization_id=organization_id,
        conversation_id=conv.id,
        role="assistant",
        content=result["content"],
        provider=result["provider"],
        model=result.get("model"),
        token_count=result.get("token_count"),
        metadata_={
            "citations": citations,
            "tools_used": tool_run["tools_used"],
            "knowledge_ids": knowledge_ids,
            "page_context": page_context or {},
            "regenerated": True,
        },
    )
    db.add(assistant)
    await db.flush()

    duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        AiRequestLog(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conv.id,
            action="chat",
            tools_used=tool_run["tools_used"],
            model=result.get("model"),
            provider=result["provider"],
            token_count=result.get("token_count"),
            duration_ms=duration_ms,
            success=success,
            prompt_preview=content[:500],
            error_code=error_code,
            metadata_={"citation_count": len(citations), "regenerated": True},
        )
    )
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_id=user_id,
        action="ai.conversation.regenerate",
        resource_type="ai_conversation",
        resource_id=str(conv.id),
        description="Regenerated AI copilot response",
        ip_address=ip,
        user_agent=user_agent,
        changes={"provider": result["provider"], "tools_used": tool_run["tools_used"]},
    )
    await db.flush()

    conv = await ai_service.get_conversation(db, organization_id, user_id, conversation_id)
    return conv, last_user, assistant, citations


def suggested_questions(org_snapshot: dict[str, Any]) -> list[str]:
    """Context-aware starter prompts derived from the org snapshot."""
    questions: list[str] = []
    if (org_snapshot.get("open_tasks_count") or 0) > 0:
        questions.append("Which tasks are overdue and who owns them?")
    if (org_snapshot.get("indicators_count") or 0) > 0:
        questions.append("Which indicators are behind target this period?")
    if (org_snapshot.get("active_grants_count") or 0) > 0:
        questions.append("Which grants are ending in the next 90 days?")
    if (org_snapshot.get("beneficiaries_count") or 0) > 0:
        questions.append("How many beneficiaries have we reached so far?")
    questions.append("Give me an executive summary of portfolio health.")
    questions.append("Draft a monthly donor report from our current data.")
    # De-duplicate while preserving order, cap at 6
    seen: set[str] = set()
    out: list[str] = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:6]


def export_conversation_markdown(conv: AiConversation) -> str:
    """Render a conversation as portable markdown."""
    lines: list[str] = [f"# {conv.title}", ""]
    lines.append(f"_Conversation {conv.id}_")
    lines.append("")
    for msg in conv.messages:
        if msg.role not in ("user", "assistant"):
            continue
        speaker = "You" if msg.role == "user" else "ImpactFlow AI"
        lines.append(f"### {speaker}")
        lines.append("")
        lines.append(msg.content)
        cites = (msg.metadata_ or {}).get("citations") if msg.role == "assistant" else None
        if cites:
            labels = ", ".join(f"[{c.get('type')}:{c.get('label')}]" for c in cites)
            lines.append("")
            lines.append(f"_Sources: {labels}_")
        lines.append("")
    return "\n".join(lines)


async def dashboard_insights(db: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    """Delegate to the deterministic intelligence module."""
    from app.services import ai_intelligence

    return await ai_intelligence.build_dashboard_insights(db, organization_id)
