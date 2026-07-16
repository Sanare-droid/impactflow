# ImpactFlow V1.3 — Epic 3: Automation & Workflow Engine

## Analysis summary

Reuse existing spine — do **not** rebuild:
- `emit_event` → in-app notifications + webhook queue
- `run_job_tick` → webhook retries, overdue/burn scans
- `mailer.send_email`, Slack via `IntegrationConnection` + `_deliver_one`
- `write_audit_log`, RBAC catalog

**Decision:** Workflows match on events (and schedules), enqueue runs, and execute actions by calling existing primitives.

## Architecture

```
Domain mutation
  └── emit_event(...)
        ├── notify_org_members (existing)
        ├── enqueue_webhooks (existing)
        └── workflows.enqueue_matching_runs  ← NEW

run_job_tick (existing loop)
  ├── process_webhook_queue
  ├── scan_overdue_tasks / scan_budget_burn
  ├── workflows.process_due_schedules     ← NEW
  └── workflows.process_run_queue         ← NEW
        └── actions → notification | email | slack/webhook | create_task | AI draft report | audit | approval wait
```

### Definition JSON (versioned)
```json
{
  "trigger": { "type": "survey.response_submitted" },
  "conditions": { "op": "and", "rules": [ { "field": "severity", "cmp": "eq", "value": "high" } ] },
  "actions": [
    { "id": "a1", "type": "send_notification", "config": { "title": "...", "role_slugs": ["manager"] } },
    { "id": "a2", "type": "approval_request", "config": { "assignee_role": "org_admin" } }
  ],
  "settings": { "stop_on_error": true }
}
```

### AI
`POST /ai/workflows/draft` returns validated definition JSON only — never executes runs.

## Delivered status (Definition of Done)

- [x] Visual workflow builder (palette / canvas / properties) + list, templates, clone
- [x] Trigger catalog + event matching via `emit_event` hook
- [x] Nested AND/OR conditions with dotted-field evaluation
- [x] Action catalog reusing notifications, email, webhooks/Slack, tasks, AI report draft, audit, approvals
- [x] Template library (8 built-ins) + clone to org
- [x] Schedules (cadence + cron field) processed in `run_job_tick`
- [x] Approval workflows (pending → approve/reject/return continues or stops run)
- [x] Execution queue with retries, step timeline, cancel, metrics
- [x] Permissions: `workflows:read|manage|approve`
- [x] AI assist drafts definition JSON (`/ai/workflows/draft`) — does not execute
- [x] Tenant isolation + audit on CRUD/runs/approvals
- [x] API **0.15.0** · migration **0014_phase14**
- [x] Tests in `tests/test_workflows.py` (8 scenarios)

## API version
**0.15.0** · Migration **0014_phase14**
