"""AI text generation: OpenAI when configured, otherwise deterministic fallback."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ImpactFlow AI, an enterprise MEAL and grants copilot for NGOs. "
    "Be concise, practical, and evidence-oriented. Prefer actionable recommendations. "
    "Grounding rules you MUST follow: "
    "Never invent numbers, metrics, names, or facts. "
    "Only use figures and facts present in the provided tool results and knowledge data; "
    "if a value is not in that data, do not state it. "
    "Cite the source of every claim inline as [type:label] (for example [program:Nutrition] "
    "or [knowledge:MEAL Handbook]). "
    "Never invent donor or beneficiary PII. "
    "If the provided data is insufficient to answer, say so explicitly and state what to collect or query next."
)


def provider_name() -> str:
    return "openai" if settings.openai_api_key.strip() else "fallback"


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    system: Optional[str] = None,
    grounding: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return {content, provider, model, token_count}.

    ``grounding`` (tool results + snapshot) is only used by the deterministic
    fallback to synthesize an answer from real data; the OpenAI path receives the
    grounding through the ``system`` prompt built by the orchestrator.
    """
    system_text = system or SYSTEM_PROMPT
    if settings.openai_api_key.strip():
        try:
            return await _openai_chat(system_text, messages)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI chat failed, using fallback: %s", exc)
    return _fallback_chat(messages, grounding=grounding)


async def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    system: Optional[str] = None,
    grounding: Optional[dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """Async generator yielding text chunks.

    Uses OpenAI streaming when configured; otherwise yields the deterministic
    fallback answer word-by-word so the UI experience is identical.
    """
    system_text = system or SYSTEM_PROMPT
    if settings.openai_api_key.strip():
        try:
            async for chunk in _openai_chat_stream(system_text, messages):
                yield chunk
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI stream failed, using fallback: %s", exc)

    result = _fallback_chat(messages, grounding=grounding)
    words = result["content"].split(" ")
    for idx, word in enumerate(words):
        yield word if idx == 0 else f" {word}"


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


async def _openai_chat_stream(
    system: str, messages: list[dict[str, str]]
) -> AsyncIterator[str]:
    payload = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": 0.3,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    parsed = json.loads(data)
                    delta = parsed["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta


def _grounded_answer(query: str, grounding: dict[str, Any]) -> Optional[str]:
    """Summarize tool/snapshot data into a grounded answer (no invented numbers)."""
    results = grounding.get("results") or {}
    if not results:
        return None

    parts: list[str] = []

    snap = None
    for key in ("org_snapshot", "analytics_overview"):
        env = results.get(key)
        if env and env.get("ok"):
            snap = env.get("data")
            break
    if isinstance(snap, dict):
        bits = []
        for label, field in (
            ("programs", "programs_count"),
            ("projects", "projects_count"),
            ("open tasks", "open_tasks_count"),
            ("active grants", "active_grants_count"),
            ("beneficiaries", "beneficiaries_count"),
            ("indicators", "indicators_count"),
        ):
            if field in snap:
                bits.append(f"{snap[field]} {label}")
        if bits:
            parts.append("Portfolio snapshot: " + ", ".join(bits) + ".")

    def _names(env_key: str, data_key: str, name_field: str, label: str) -> None:
        env = results.get(env_key)
        if not env or not env.get("ok"):
            return
        rows = (env.get("data") or {}).get(data_key) or []
        if not rows:
            parts.append(f"No {label} matched.")
            return
        names = [str(r.get(name_field) or r.get("code") or r.get("id")) for r in rows[:5]]
        total = (env.get("data") or {}).get("total", len(rows))
        parts.append(f"{label.capitalize()} ({total}): " + ", ".join(names) + ".")

    _names("search_beneficiaries", "beneficiaries", "name", "beneficiaries")
    _names("search_projects", "projects", "name", "projects")
    _names("search_programs", "programs", "name", "programs")
    _names("search_grants", "grants", "name", "grants")
    _names("search_indicators", "indicators", "name", "indicators")
    _names("search_surveys", "surveys", "name", "surveys")
    _names("search_reports", "reports", "name", "reports")
    _names("search_evidence", "evidence", "title", "evidence")

    tasks_env = results.get("search_activities_tasks")
    if tasks_env and tasks_env.get("ok"):
        tdata = tasks_env.get("data") or {}
        parts.append(
            f"Tasks: {tdata.get('open_tasks_total', 0)} open, "
            f"{tdata.get('overdue_count', 0)} overdue."
        )

    prog_env = results.get("indicator_progress")
    if prog_env and prog_env.get("ok"):
        rows = (prog_env.get("data") or {}).get("progress") or []
        behind = [r for r in rows if r.get("progress_pct") is not None and r["progress_pct"] < 70]
        if behind:
            names = [f"{r['name']} ({r['progress_pct']}%)" for r in behind[:5]]
            parts.append("Indicators behind target: " + ", ".join(names) + ".")

    know_env = results.get("search_knowledge")
    if know_env and know_env.get("ok"):
        docs = (know_env.get("data") or {}).get("documents") or []
        if docs:
            parts.append(
                "Relevant knowledge: "
                + ", ".join(f"[knowledge:{d['name']}]" for d in docs[:3])
                + "."
            )

    if not parts:
        return None
    return " ".join(parts)


def _fallback_chat(
    messages: list[dict[str, str]],
    *,
    grounding: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    lower = last.lower()

    if grounding:
        grounded = _grounded_answer(last, grounding)
        if grounded:
            return {
                "content": grounded
                + " (Grounded from your organization's live data — set OPENAI_API_KEY for richer phrasing.)",
                "provider": "fallback",
                "model": None,
                "token_count": None,
            }

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
