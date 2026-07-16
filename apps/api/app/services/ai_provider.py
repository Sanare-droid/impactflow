"""AI text generation: OpenAI when configured, otherwise deterministic fallback."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ImpactFlow AI, an enterprise MEAL and grants copilot for NGOs. "
    "Be concise, practical, and evidence-oriented. Prefer actionable recommendations. "
    "Never invent donor or beneficiary PII. If data is missing, say what to collect next."
)


def provider_name() -> str:
    return "openai" if settings.openai_api_key.strip() else "fallback"


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    system: Optional[str] = None,
) -> dict[str, Any]:
    """Return {content, provider, model, token_count}."""
    system_text = system or SYSTEM_PROMPT
    if settings.openai_api_key.strip():
        try:
            return await _openai_chat(system_text, messages)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI chat failed, using fallback: %s", exc)
    return _fallback_chat(messages)


async def generate_prediction_text(context: dict[str, Any]) -> dict[str, Any]:
    prompt = (
        "Given this organization delivery/finance/MEAL snapshot, produce a JSON object with keys: "
        "title (string), summary (string), severity (low|medium|high|critical), score (0-100 number), "
        "recommendations (array of short strings). Snapshot:\n"
        f"{json.dumps(context, default=str)}"
    )
    result = await chat_completion(
        [{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT + " Respond with valid JSON only.",
    )
    parsed = _try_parse_json(result["content"])
    if not parsed:
        parsed = _heuristic_prediction(context)
    return {
        **parsed,
        "provider": result["provider"],
        "model": result.get("model"),
    }


async def generate_narrative_text(
    narrative_type: str,
    context: dict[str, Any],
    *,
    prompt: Optional[str] = None,
) -> dict[str, Any]:
    user_prompt = prompt or (
        f"Write a {narrative_type.replace('_', ' ')} narrative for an NGO program portfolio. "
        f"Use this context:\n{json.dumps(context, default=str)}\n"
        "Write 2-4 short paragraphs suitable for a donor report. No markdown headings."
    )
    result = await chat_completion([{"role": "user", "content": user_prompt}])
    return {
        "content": result["content"],
        "provider": result["provider"],
        "model": result.get("model"),
    }


async def _openai_chat(system: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    payload = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    choice = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return {
        "content": choice.strip(),
        "provider": "openai",
        "model": data.get("model") or settings.openai_model,
        "token_count": usage.get("total_tokens"),
    }


def _fallback_chat(messages: list[dict[str, str]]) -> dict[str, Any]:
    last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    lower = last.lower()
    if "risk" in lower or "predict" in lower:
        content = (
            "Based on current portfolio signals, prioritize projects with delayed tasks, "
            "low monitoring coverage, and high budget burn. Review open high-severity risks, "
            "confirm indicator baselines, and schedule a mid-cycle delivery check-in. "
            "(Deterministic fallback — set OPENAI_API_KEY for model-backed answers.)"
        )
    elif "narrative" in lower or "report" in lower:
        content = (
            "Draft narrative: During this period the organization advanced delivery across active "
            "programs while strengthening MEAL evidence. Next period should focus on closing "
            "indicator gaps, verifying field evidence, and aligning donor updates to verified results. "
            "(Deterministic fallback — set OPENAI_API_KEY for richer drafts.)"
        )
    elif "knowledge" in lower or "sop" in lower:
        content = (
            "Search the knowledge base for SOPs on indicator verification, beneficiary consent, "
            "and evidence filing. If no matching article exists, create one under Knowledge Base "
            "and tag it for field officers. "
            "(Deterministic fallback — set OPENAI_API_KEY for grounded answers.)"
        )
    else:
        content = (
            f"I received your question about ImpactFlow operations. "
            f"Suggested next steps: (1) check Analytics for portfolio health, "
            f"(2) review open Predictions, (3) draft a Narrative for stakeholder updates. "
            f"Question excerpt: {last[:280] or '(empty)'}. "
            f"(Deterministic fallback — set OPENAI_API_KEY for model-backed answers.)"
        )
    return {
        "content": content,
        "provider": "fallback",
        "model": None,
        "token_count": None,
    }


def _try_parse_json(text: str) -> Optional[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                return None
    return None


def _heuristic_prediction(context: dict[str, Any]) -> dict[str, Any]:
    open_tasks = int(context.get("open_tasks_count") or 0)
    monitoring = int(context.get("monitoring_results_count") or 0)
    indicators = int(context.get("indicators_count") or 0)
    expenses = float(context.get("expenses_total") or 0)
    awarded = float(context.get("grants_awarded_total") or 0)

    score = 35.0
    if open_tasks > 10:
        score += 15
    if indicators > 0 and monitoring < max(1, indicators // 2):
        score += 20
    if awarded > 0 and expenses / awarded > 0.85:
        score += 20
    score = min(95.0, score)

    if score >= 75:
        severity = "high"
    elif score >= 55:
        severity = "medium"
    else:
        severity = "low"

    return {
        "title": "Portfolio delivery risk scan",
        "summary": (
            f"Heuristic scan found open_tasks={open_tasks}, monitoring={monitoring}/"
            f"{indicators} indicators, burn≈{expenses:.0f}/{awarded:.0f}. "
            "Prioritize delayed workstreams and under-reported indicators."
        ),
        "severity": severity,
        "score": score,
        "recommendations": [
            "Close or reassign overdue tasks",
            "Increase monitoring coverage for active indicators",
            "Review budget burn against grant milestones",
        ],
    }
