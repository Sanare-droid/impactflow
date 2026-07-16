# ImpactFlow V1.2 — Epic 2: AI Copilot & Organizational Intelligence

## Analysis summary

Phase 7 already provides:
- `AiConversation` / `AiMessage`, knowledge RAG (`search_knowledge`), predictions, narratives
- Single LLM boundary: `ai_provider.py` (OpenAI or deterministic fallback)
- Permissions: `ai:use`, `predictions:*`, `narratives:*`, `knowledge:*`

**Decision:** Extend — do **not** create a second chat/LLM/knowledge stack.

## Architecture

```
Router (ai.py)
  └── ai.send_message / stream / insights / reports / …
        └── ai_orchestrator.run_turn
              ├── ai_tools (permission-filtered, org-scoped)
              ├── search_knowledge (swappable retrieval adapter)
              ├── ai_provider.chat_completion (+ stream)
              └── citations + ai_request_logs (no response body logged)
```

### Grounding rule
Answers must only use tool results + knowledge hits. Never invent metrics. Cite as `[type:label]`.

### Retrieval adapter
`search_knowledge` remains the port; pgvector can replace internals later without changing Copilot API.

## Deliverables
API 0.14 · migration 0013 · tool-grounded chat · dashboard insights · deterministic risk scan · premium Copilot UI

## Delivered status (Definition of Done)

- [x] **Tool-grounded chat** — `ai_tools` (permission-filtered, org-scoped) + `search_knowledge` retrieval feed `ai_orchestrator.run_turn`.
- [x] **Citations reach the client** — assistant `metadata.citations` + `tools_used`; `[type:label]` grounding enforced in `SYSTEM_PROMPT`.
- [x] **Streaming** — `POST /ai/conversations/{id}/messages/stream` (SSE token/tool events) via `ai_provider` stream.
- [x] **Regenerate** — `ai_orchestrator.regenerate_turn` re-answers the last user turn without duplicating the user message.
- [x] **Message feedback** — `POST /ai/messages/{id}/feedback` (thumbs up/down) stored on message metadata.
- [x] **Pin / list filter** — `AiConversation.pinned`; `GET /ai/conversations?pinned=` filter; pinned-first ordering.
- [x] **Share** — `POST /ai/conversations/{id}/share` issues a `secrets.token_urlsafe(16)` token (same-user for now; stored for future public view) and returns `url_path`.
- [x] **Export** — `GET /ai/conversations/{id}/export` returns portable Markdown with sources.
- [x] **Dashboard insights** — `GET /ai/insights/dashboard` (allows `dashboard:read` OR `ai:use`) surfaced on the web dashboard card.
- [x] **Suggested questions** — `GET /ai/suggested-questions` from the org snapshot.
- [x] **Deterministic risk scan** — `POST /ai/insights/scan` (optional persist to predictions).
- [x] **Structured reports** — `POST /ai/reports/generate` returns grounded Markdown; optional save as narrative.
- [x] **Observability** — `AiRequestLog` records tools/model/provider/success without storing response bodies.
- [x] **Tenant isolation** — conversations, tools, and knowledge are strictly org-scoped (cross-tenant returns 404).
- [x] **Migration** — `0013_phase13` applied (pinned, share_token, request logs).
- [x] **API version** — `API_VERSION = 0.14.0`.
- [x] **Premium web UI** — Copilot page + dashboard insights card.
- [x] **Tests** — `tests/test_ai_copilot.py` covers tool selection, tenant scoping, citations, insights, cross-tenant 404, suggested questions, regenerate (no duplicate user message), pin, report Markdown, and message feedback.
