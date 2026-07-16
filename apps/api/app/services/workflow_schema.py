"""Workflow definition schema: catalogs, validation, condition engine, templates.

A workflow *definition* is a JSON document with the shape::

    {
      "trigger": {"type": "beneficiary.registered", "conditions": {...} | null},
      "actions": [
        {"id": "notify", "type": "send_notification", "name": "...", "config": {...}},
        ...
      ],
      "settings": {"max_attempts": 5}
    }

Conditions are a nested boolean tree::

    {"op": "and", "rules": [
        {"field": "metadata.severity", "cmp": "in", "value": ["high", "critical"]},
        {"op": "or", "rules": [ ... ]}
    ]}

Leaf rules resolve ``field`` via dotted path against a merged lookup built from
the trigger payload and run context (e.g. ``metadata.severity``,
``trigger.event``, ``context.foo``).
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.exceptions import AppError

# --------------------------------------------------------------------------- #
# Catalogs
# --------------------------------------------------------------------------- #

TRIGGER_TYPES: list[dict[str, str]] = [
    {"code": "project.created", "label": "Project created", "category": "project"},
    {"code": "project.updated", "label": "Project updated", "category": "project"},
    {"code": "project.completed", "label": "Project completed", "category": "project"},
    {"code": "activity.created", "label": "Activity created", "category": "activity"},
    {"code": "activity.updated", "label": "Activity updated", "category": "activity"},
    {"code": "activity.completed", "label": "Activity completed", "category": "activity"},
    {"code": "task.created", "label": "Task created", "category": "task"},
    {"code": "task.overdue", "label": "Task overdue", "category": "task"},
    {"code": "task.completed", "label": "Task completed", "category": "task"},
    {"code": "grant.created", "label": "Grant created", "category": "grant"},
    {"code": "grant.expiring", "label": "Grant expiring", "category": "grant"},
    {"code": "survey.published", "label": "Survey published", "category": "survey"},
    {
        "code": "survey.response_submitted",
        "label": "Survey response submitted",
        "category": "survey",
    },
    {
        "code": "beneficiary.registered",
        "label": "Beneficiary registered",
        "category": "beneficiary",
    },
    {"code": "beneficiary.updated", "label": "Beneficiary updated", "category": "beneficiary"},
    {"code": "indicator.updated", "label": "Indicator updated", "category": "indicator"},
    {
        "code": "indicator.below_target",
        "label": "Indicator below target",
        "category": "indicator",
    },
    {"code": "prediction.opened", "label": "Prediction opened", "category": "ai"},
    {"code": "report.published", "label": "Report published", "category": "report"},
    {"code": "document.uploaded", "label": "Document uploaded", "category": "document"},
    {"code": "webhook.received", "label": "Inbound webhook received", "category": "integration"},
    {"code": "schedule", "label": "Scheduled time", "category": "schedule"},
    {"code": "manual", "label": "Manual run", "category": "manual"},
    {"code": "ai.insight_generated", "label": "AI insight generated", "category": "ai"},
    {"code": "budget.burn", "label": "Budget burn threshold", "category": "finance"},
    {"code": "user.invited", "label": "User invited", "category": "user"},
    {"code": "integration.error", "label": "Integration error", "category": "integration"},
]

ACTION_TYPES: list[dict[str, str]] = [
    {"code": "send_notification", "label": "Send in-app notification", "category": "notify"},
    {"code": "send_email", "label": "Send email", "category": "notify"},
    {"code": "send_slack", "label": "Send Slack / outbound message", "category": "notify"},
    {"code": "create_task", "label": "Create task", "category": "record"},
    {"code": "assign_user", "label": "Assign user to task", "category": "record"},
    {"code": "generate_ai_report", "label": "Generate AI report (draft)", "category": "ai"},
    {
        "code": "generate_executive_summary",
        "label": "Generate executive summary (draft)",
        "category": "ai",
    },
    {"code": "update_record", "label": "Update record fields", "category": "record"},
    {"code": "create_audit_event", "label": "Create audit event", "category": "system"},
    {"code": "log_message", "label": "Log message", "category": "system"},
    {"code": "call_webhook", "label": "Call webhook (queued)", "category": "integration"},
    {"code": "http_request", "label": "HTTP request", "category": "integration"},
    {"code": "delay", "label": "Delay / wait", "category": "control"},
    {"code": "approval_request", "label": "Request approval", "category": "control"},
    {"code": "terminate_workflow", "label": "Terminate workflow", "category": "control"},
    {"code": "branch_noop", "label": "Condition branch (no-op)", "category": "control"},
]

CONDITION_OPERATORS: list[dict[str, str]] = [
    {"code": "eq", "label": "Equals"},
    {"code": "neq", "label": "Not equals"},
    {"code": "contains", "label": "Contains"},
    {"code": "starts_with", "label": "Starts with"},
    {"code": "ends_with", "label": "Ends with"},
    {"code": "gt", "label": "Greater than"},
    {"code": "lt", "label": "Less than"},
    {"code": "gte", "label": "Greater than or equal"},
    {"code": "lte", "label": "Less than or equal"},
    {"code": "between", "label": "Between (inclusive)"},
    {"code": "empty", "label": "Is empty"},
    {"code": "not_empty", "label": "Is not empty"},
    {"code": "in", "label": "In list"},
    {"code": "not_in", "label": "Not in list"},
]

_TRIGGER_CODES = {t["code"] for t in TRIGGER_TYPES}
_ACTION_CODES = {a["code"] for a in ACTION_TYPES}
_OPERATOR_CODES = {o["code"] for o in CONDITION_OPERATORS}

# Aliases so a workflow trigger can match multiple raw event names.
TRIGGER_ALIASES: dict[str, list[str]] = {
    "task.overdue": ["task.overdue"],
    "budget.burn": ["budget.burn"],
    "indicator.below_target": ["indicator.below_target", "indicator.updated"],
}


def list_trigger_types() -> list[dict[str, str]]:
    return [dict(t) for t in TRIGGER_TYPES]


def list_action_types() -> list[dict[str, str]]:
    return [dict(a) for a in ACTION_TYPES]


def list_condition_operators() -> list[dict[str, str]]:
    return [dict(o) for o in CONDITION_OPERATORS]


# --------------------------------------------------------------------------- #
# Normalization & validation
# --------------------------------------------------------------------------- #


def normalize_definition(definition: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Return a definition dict with defaults filled in (non-destructive copy)."""
    src = dict(definition or {})

    raw_trigger = src.get("trigger") or {}
    if isinstance(raw_trigger, str):
        raw_trigger = {"type": raw_trigger}
    trigger = {
        "type": str(raw_trigger.get("type") or "manual"),
        "conditions": raw_trigger.get("conditions"),
    }
    # allow extra trigger metadata (e.g. schedule hints) to pass through
    for key, value in raw_trigger.items():
        if key not in trigger:
            trigger[key] = value

    actions: list[dict[str, Any]] = []
    for idx, raw in enumerate(src.get("actions") or []):
        if not isinstance(raw, dict):
            continue
        action_id = str(raw.get("id") or f"step_{idx + 1}")
        actions.append(
            {
                "id": action_id,
                "type": str(raw.get("type") or "log_message"),
                "name": raw.get("name") or action_id,
                "config": dict(raw.get("config") or {}),
                "conditions": raw.get("conditions"),
            }
        )

    settings = dict(src.get("settings") or {})
    try:
        settings["max_attempts"] = int(settings.get("max_attempts") or 5)
    except (TypeError, ValueError):
        settings["max_attempts"] = 5

    return {
        "trigger": trigger,
        "actions": actions,
        "settings": settings,
    }


def validate_definition(definition: dict[str, Any]) -> None:
    """Validate a (normalized or raw) definition, raising ``AppError`` (422)."""
    norm = normalize_definition(definition)

    trigger_type = norm["trigger"]["type"]
    if trigger_type not in _TRIGGER_CODES:
        raise AppError(
            f"Unknown trigger type: {trigger_type}",
            code="VALIDATION_ERROR",
            status_code=422,
            details={"trigger_type": trigger_type},
        )

    _validate_conditions(norm["trigger"].get("conditions"))

    actions = norm["actions"]
    if not actions:
        raise AppError(
            "Workflow must define at least one action",
            code="VALIDATION_ERROR",
            status_code=422,
        )

    seen_ids: set[str] = set()
    for action in actions:
        atype = action["type"]
        if atype not in _ACTION_CODES:
            raise AppError(
                f"Unknown action type: {atype}",
                code="VALIDATION_ERROR",
                status_code=422,
                details={"action_type": atype},
            )
        aid = action["id"]
        if aid in seen_ids:
            raise AppError(
                f"Duplicate action id: {aid}",
                code="VALIDATION_ERROR",
                status_code=422,
                details={"action_id": aid},
            )
        seen_ids.add(aid)
        _validate_conditions(action.get("conditions"))


def _validate_conditions(conditions: Any) -> None:
    if conditions in (None, {}, []):
        return
    if not isinstance(conditions, dict):
        raise AppError(
            "Conditions must be an object",
            code="VALIDATION_ERROR",
            status_code=422,
        )
    if "op" in conditions and conditions["op"] in ("and", "or"):
        rules = conditions.get("rules")
        if not isinstance(rules, list):
            raise AppError(
                "Boolean condition requires a 'rules' list",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        for rule in rules:
            _validate_conditions(rule)
        return
    # leaf
    cmp = conditions.get("cmp") or conditions.get("op")
    if cmp not in _OPERATOR_CODES:
        raise AppError(
            f"Unknown condition operator: {cmp}",
            code="VALIDATION_ERROR",
            status_code=422,
            details={"operator": cmp},
        )
    if "field" not in conditions:
        raise AppError(
            "Condition leaf requires a 'field'",
            code="VALIDATION_ERROR",
            status_code=422,
        )


# --------------------------------------------------------------------------- #
# Condition evaluation
# --------------------------------------------------------------------------- #


def _resolve_path(path: str, source: dict[str, Any]) -> Any:
    current: Any = source
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _as_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compare(cmp: str, actual: Any, expected: Any) -> bool:
    if cmp == "empty":
        return actual in (None, "", [], {}, ())
    if cmp == "not_empty":
        return actual not in (None, "", [], {}, ())
    if cmp == "eq":
        return actual == expected
    if cmp == "neq":
        return actual != expected
    if cmp == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    if cmp == "starts_with":
        return isinstance(actual, str) and actual.startswith(str(expected))
    if cmp == "ends_with":
        return isinstance(actual, str) and actual.endswith(str(expected))
    if cmp in ("gt", "lt", "gte", "lte"):
        a = _as_number(actual)
        b = _as_number(expected)
        if a is None or b is None:
            return False
        if cmp == "gt":
            return a > b
        if cmp == "lt":
            return a < b
        if cmp == "gte":
            return a >= b
        return a <= b
    if cmp == "between":
        if not isinstance(expected, (list, tuple)) or len(expected) != 2:
            return False
        a = _as_number(actual)
        low = _as_number(expected[0])
        high = _as_number(expected[1])
        if a is None or low is None or high is None:
            return False
        return low <= a <= high
    if cmp == "in":
        try:
            return actual in expected
        except TypeError:
            return False
    if cmp == "not_in":
        try:
            return actual not in expected
        except TypeError:
            return True
    return False


def evaluate_conditions(
    conditions: Any,
    payload: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
) -> bool:
    """Evaluate a condition tree against payload/context. Empty conditions pass."""
    if conditions in (None, {}, []):
        return True
    if not isinstance(conditions, dict):
        return True

    source: dict[str, Any] = {}
    source["trigger"] = payload or {}
    source["context"] = context or {}
    if isinstance(payload, dict):
        source.update(payload)
    if isinstance(context, dict):
        for key, value in context.items():
            source.setdefault(key, value)

    return _eval_node(conditions, source)


def _eval_node(node: dict[str, Any], source: dict[str, Any]) -> bool:
    if "op" in node and node["op"] in ("and", "or"):
        rules = node.get("rules") or []
        results = [_eval_node(r, source) for r in rules if isinstance(r, dict)]
        if node["op"] == "and":
            return all(results) if results else True
        return any(results) if results else False
    cmp = node.get("cmp") or node.get("op")
    actual = _resolve_path(node.get("field", ""), source)
    return _compare(str(cmp), actual, node.get("value"))


# --------------------------------------------------------------------------- #
# Built-in templates
# --------------------------------------------------------------------------- #

TEMPLATES: list[dict[str, Any]] = [
    {
        "code": "new-beneficiary-welcome",
        "name": "New Beneficiary Welcome",
        "category": "beneficiaries",
        "description": "Notify field team when a beneficiary is registered.",
        "definition": {
            "trigger": {"type": "beneficiary.registered", "conditions": None},
            "actions": [
                {
                    "id": "notify_team",
                    "type": "send_notification",
                    "name": "Notify field team",
                    "config": {
                        "title": "New beneficiary registered: {{trigger.title}}",
                        "body": "A new beneficiary was added to your program.",
                        "severity": "info",
                        "role_slugs": ["org_admin", "manager", "field_officer"],
                        "link": "/app/beneficiaries",
                    },
                },
                {
                    "id": "log",
                    "type": "log_message",
                    "name": "Log registration",
                    "config": {"message": "Welcome workflow ran for {{trigger.title}}"},
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "grant-deadline-reminder",
        "name": "Grant Deadline Reminder",
        "category": "grants",
        "description": "Alert managers when a grant is expiring soon.",
        "definition": {
            "trigger": {"type": "grant.expiring", "conditions": None},
            "actions": [
                {
                    "id": "notify_managers",
                    "type": "send_notification",
                    "name": "Notify managers",
                    "config": {
                        "title": "Grant expiring: {{trigger.title}}",
                        "body": "Review reporting and renewal actions before the deadline.",
                        "severity": "warning",
                        "role_slugs": ["org_admin", "manager"],
                        "link": "/app/grants",
                    },
                },
                {
                    "id": "email_admin",
                    "type": "send_email",
                    "name": "Email admins",
                    "config": {
                        "subject": "Grant expiring: {{trigger.title}}",
                        "body": "A grant is approaching its end date. Please review.",
                        "link": "/app/grants",
                        "role_slugs": ["org_admin"],
                    },
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "survey-reminder",
        "name": "Survey Reminder",
        "category": "surveys",
        "description": "Notify officers when a survey is published.",
        "definition": {
            "trigger": {"type": "survey.published", "conditions": None},
            "actions": [
                {
                    "id": "notify",
                    "type": "send_notification",
                    "name": "Notify data collectors",
                    "config": {
                        "title": "Survey ready: {{trigger.title}}",
                        "body": "A new survey is live for data collection.",
                        "severity": "info",
                        "role_slugs": ["field_officer", "meal_officer"],
                        "link": "/app/surveys",
                    },
                }
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "indicator-warning",
        "name": "Indicator Warning",
        "category": "meal",
        "description": "Escalate when an indicator falls below target.",
        "definition": {
            "trigger": {
                "type": "indicator.below_target",
                "conditions": {
                    "op": "and",
                    "rules": [
                        {"field": "metadata.progress_pct", "cmp": "lt", "value": 70}
                    ],
                },
            },
            "actions": [
                {
                    "id": "notify_meal",
                    "type": "send_notification",
                    "name": "Notify MEAL",
                    "config": {
                        "title": "Indicator below target: {{trigger.title}}",
                        "body": "An indicator is behind its target and needs attention.",
                        "severity": "warning",
                        "role_slugs": ["meal_officer", "manager"],
                        "link": "/app/indicators",
                    },
                },
                {
                    "id": "summary",
                    "type": "generate_executive_summary",
                    "name": "Draft summary",
                    "config": {"report_type": "executive_brief"},
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "task-escalation",
        "name": "Task Escalation",
        "category": "operations",
        "description": "Escalate overdue tasks to managers with approval.",
        "definition": {
            "trigger": {"type": "task.overdue", "conditions": None},
            "actions": [
                {
                    "id": "notify",
                    "type": "send_notification",
                    "name": "Notify managers",
                    "config": {
                        "title": "Overdue task escalated: {{trigger.title}}",
                        "body": "This task is overdue and has been escalated.",
                        "severity": "warning",
                        "role_slugs": ["org_admin", "manager"],
                        "link": "/app/tasks",
                    },
                },
                {
                    "id": "approval",
                    "type": "approval_request",
                    "name": "Manager approval",
                    "config": {
                        "title": "Approve escalation for {{trigger.title}}",
                        "role_slugs": ["manager"],
                    },
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "budget-alert",
        "name": "Budget Alert",
        "category": "finance",
        "description": "Alert finance when budget burn crosses threshold.",
        "definition": {
            "trigger": {"type": "budget.burn", "conditions": None},
            "actions": [
                {
                    "id": "notify_finance",
                    "type": "send_notification",
                    "name": "Notify finance",
                    "config": {
                        "title": "Budget burn alert: {{trigger.title}}",
                        "body": "{{trigger.body}}",
                        "severity": "critical",
                        "role_slugs": ["org_admin", "manager"],
                        "link": "/app/budgets",
                    },
                },
                {
                    "id": "slack",
                    "type": "send_slack",
                    "name": "Post to Slack",
                    "config": {
                        "title": "Budget burn alert: {{trigger.title}}",
                        "body": "{{trigger.body}}",
                    },
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "quarterly-report-automation",
        "name": "Quarterly Report Automation",
        "category": "reporting",
        "description": "Generate a draft executive report every quarter.",
        "definition": {
            "trigger": {"type": "schedule", "conditions": None, "cadence": "quarterly"},
            "actions": [
                {
                    "id": "report",
                    "type": "generate_ai_report",
                    "name": "Draft quarterly report",
                    "config": {"report_type": "quarterly_summary"},
                },
                {
                    "id": "notify",
                    "type": "send_notification",
                    "name": "Notify leadership",
                    "config": {
                        "title": "Quarterly report drafted",
                        "body": "A draft quarterly report is ready for review.",
                        "severity": "info",
                        "role_slugs": ["org_admin", "manager"],
                        "link": "/app/narratives",
                    },
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
    {
        "code": "risk-escalation",
        "name": "Risk Escalation",
        "category": "ai",
        "description": "Escalate high-severity predictions to leadership.",
        "definition": {
            "trigger": {
                "type": "prediction.opened",
                "conditions": {
                    "op": "and",
                    "rules": [
                        {
                            "field": "metadata.severity",
                            "cmp": "in",
                            "value": ["high", "critical"],
                        }
                    ],
                },
            },
            "actions": [
                {
                    "id": "notify_leadership",
                    "type": "send_notification",
                    "name": "Notify leadership",
                    "config": {
                        "title": "High-severity risk: {{trigger.title}}",
                        "body": "A high-severity prediction requires review.",
                        "severity": "critical",
                        "role_slugs": ["org_admin", "manager", "meal_officer"],
                        "link": "/app/predictions",
                    },
                },
                {
                    "id": "audit",
                    "type": "create_audit_event",
                    "name": "Record escalation",
                    "config": {"description": "Risk escalation workflow ran"},
                },
            ],
            "settings": {"max_attempts": 3},
        },
    },
]


def list_templates() -> list[dict[str, Any]]:
    return [dict(t) for t in TEMPLATES]


def get_template(code: str) -> Optional[dict[str, Any]]:
    for tpl in TEMPLATES:
        if tpl["code"] == code:
            return dict(tpl)
    return None
