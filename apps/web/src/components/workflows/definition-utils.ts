import type {
  WorkflowAction,
  WorkflowCatalogItem,
  WorkflowConditionGroup,
  WorkflowConditionLeaf,
  WorkflowConditionNode,
  WorkflowDefinition,
  WorkflowOperator,
} from "@/lib/api";

let idCounter = 0;

/** Short client-side unique id for a new action. The API re-normalizes ids on
 * save so cross-session collisions are not a concern. */
export function newActionId(): string {
  idCounter += 1;
  return `step_${Date.now().toString(36)}${idCounter.toString(36)}`;
}

// --------------------------------------------------------------------------- //
// Fallback catalogs (used until the API catalogs resolve, or if they fail)
// --------------------------------------------------------------------------- //

export const FALLBACK_TRIGGERS: WorkflowCatalogItem[] = [
  { code: "manual", label: "Manual run", category: "manual" },
  { code: "schedule", label: "Scheduled time", category: "schedule" },
  { code: "project.created", label: "Project created", category: "project" },
  { code: "task.overdue", label: "Task overdue", category: "task" },
  { code: "task.completed", label: "Task completed", category: "task" },
  { code: "grant.expiring", label: "Grant expiring", category: "grant" },
  { code: "survey.published", label: "Survey published", category: "survey" },
  {
    code: "survey.response_submitted",
    label: "Survey response submitted",
    category: "survey",
  },
  {
    code: "beneficiary.registered",
    label: "Beneficiary registered",
    category: "beneficiary",
  },
  {
    code: "indicator.below_target",
    label: "Indicator below target",
    category: "indicator",
  },
  { code: "prediction.opened", label: "Prediction opened", category: "ai" },
  { code: "report.published", label: "Report published", category: "report" },
  { code: "budget.burn", label: "Budget burn threshold", category: "finance" },
];

export const FALLBACK_ACTIONS: WorkflowCatalogItem[] = [
  { code: "send_notification", label: "Send in-app notification", category: "notify" },
  { code: "send_email", label: "Send email", category: "notify" },
  { code: "send_slack", label: "Send Slack / outbound message", category: "notify" },
  { code: "create_task", label: "Create task", category: "record" },
  { code: "assign_user", label: "Assign user to task", category: "record" },
  { code: "update_record", label: "Update record fields", category: "record" },
  { code: "generate_ai_report", label: "Generate AI report (draft)", category: "ai" },
  {
    code: "generate_executive_summary",
    label: "Generate executive summary (draft)",
    category: "ai",
  },
  { code: "create_audit_event", label: "Create audit event", category: "system" },
  { code: "log_message", label: "Log message", category: "system" },
  { code: "call_webhook", label: "Call webhook (queued)", category: "integration" },
  { code: "http_request", label: "HTTP request", category: "integration" },
  { code: "delay", label: "Delay / wait", category: "control" },
  { code: "approval_request", label: "Request approval", category: "control" },
  { code: "terminate_workflow", label: "Terminate workflow", category: "control" },
];

export const FALLBACK_OPERATORS: WorkflowOperator[] = [
  { code: "eq", label: "Equals" },
  { code: "neq", label: "Not equals" },
  { code: "contains", label: "Contains" },
  { code: "starts_with", label: "Starts with" },
  { code: "ends_with", label: "Ends with" },
  { code: "gt", label: "Greater than" },
  { code: "lt", label: "Less than" },
  { code: "gte", label: "Greater than or equal" },
  { code: "lte", label: "Less than or equal" },
  { code: "between", label: "Between (inclusive)" },
  { code: "empty", label: "Is empty" },
  { code: "not_empty", label: "Is not empty" },
  { code: "in", label: "In list" },
  { code: "not_in", label: "Not in list" },
];

export const CATEGORY_LABELS: Record<string, string> = {
  manual: "Manual",
  schedule: "Schedule",
  project: "Project",
  activity: "Activity",
  task: "Task",
  grant: "Grant",
  survey: "Survey",
  beneficiary: "Beneficiary",
  indicator: "Indicator",
  ai: "AI",
  report: "Report",
  document: "Document",
  integration: "Integration",
  finance: "Finance",
  user: "User",
  notify: "Notify",
  record: "Records",
  system: "System",
  control: "Control",
};

export function catalogLabel(
  items: WorkflowCatalogItem[],
  code: string,
): string {
  return items.find((i) => i.code === code)?.label || code;
}

export function operatorLabel(items: WorkflowOperator[], code: string): string {
  return items.find((i) => i.code === code)?.label || code;
}

// --------------------------------------------------------------------------- //
// Action config field schemas
// --------------------------------------------------------------------------- //

export type ConfigFieldKind = "text" | "textarea" | "list" | "select" | "number";

export type ConfigFieldDef = {
  key: string;
  label: string;
  kind: ConfigFieldKind;
  placeholder?: string;
  options?: { value: string; label: string }[];
  help?: string;
};

const SEVERITY_OPTIONS = [
  { value: "info", label: "Info" },
  { value: "success", label: "Success" },
  { value: "warning", label: "Warning" },
  { value: "critical", label: "Critical" },
];

/** Config fields rendered in the properties panel per action type. Any other
 * config keys can still be edited via the raw JSON fallback. */
export const ACTION_CONFIG_FIELDS: Record<string, ConfigFieldDef[]> = {
  send_notification: [
    { key: "title", label: "Title", kind: "text", placeholder: "New event: {{trigger.title}}" },
    { key: "body", label: "Body", kind: "textarea" },
    { key: "severity", label: "Severity", kind: "select", options: SEVERITY_OPTIONS },
    {
      key: "role_slugs",
      label: "Notify roles",
      kind: "list",
      placeholder: "org_admin, manager",
      help: "Comma-separated role slugs.",
    },
    { key: "link", label: "Link", kind: "text", placeholder: "/app/tasks" },
  ],
  send_email: [
    { key: "subject", label: "Subject", kind: "text" },
    { key: "body", label: "Body", kind: "textarea" },
    {
      key: "role_slugs",
      label: "Recipient roles",
      kind: "list",
      placeholder: "org_admin",
      help: "Comma-separated role slugs.",
    },
  ],
  send_slack: [
    { key: "title", label: "Title", kind: "text" },
    { key: "body", label: "Body", kind: "textarea" },
  ],
  create_task: [
    { key: "title", label: "Task title", kind: "text" },
    { key: "description", label: "Description", kind: "textarea" },
    { key: "priority", label: "Priority", kind: "text", placeholder: "medium" },
  ],
  assign_user: [
    {
      key: "role_slugs",
      label: "Assign roles",
      kind: "list",
      placeholder: "field_officer",
      help: "Comma-separated role slugs.",
    },
  ],
  update_record: [
    { key: "field", label: "Field", kind: "text" },
    { key: "value", label: "Value", kind: "text" },
  ],
  generate_ai_report: [
    { key: "report_type", label: "Report type", kind: "text", placeholder: "quarterly_summary" },
  ],
  generate_executive_summary: [
    { key: "report_type", label: "Report type", kind: "text", placeholder: "executive_brief" },
  ],
  create_audit_event: [
    { key: "description", label: "Description", kind: "text" },
  ],
  log_message: [{ key: "message", label: "Message", kind: "textarea" }],
  call_webhook: [
    { key: "url", label: "Webhook URL", kind: "text" },
    { key: "integration", label: "Integration name", kind: "text" },
  ],
  http_request: [
    { key: "url", label: "URL", kind: "text" },
    {
      key: "method",
      label: "Method",
      kind: "select",
      options: [
        { value: "GET", label: "GET" },
        { value: "POST", label: "POST" },
        { value: "PUT", label: "PUT" },
        { value: "PATCH", label: "PATCH" },
        { value: "DELETE", label: "DELETE" },
      ],
    },
    { key: "body", label: "Body", kind: "textarea" },
  ],
  delay: [{ key: "seconds", label: "Delay (seconds)", kind: "number" }],
  approval_request: [
    { key: "title", label: "Approval title", kind: "text" },
    {
      key: "role_slugs",
      label: "Approver roles",
      kind: "list",
      placeholder: "manager",
      help: "Comma-separated role slugs.",
    },
  ],
  terminate_workflow: [{ key: "reason", label: "Reason", kind: "text" }],
  branch_noop: [],
};

export function configFieldsFor(type: string): ConfigFieldDef[] {
  return ACTION_CONFIG_FIELDS[type] ?? [];
}

/** Sensible default config seeded when a new action is added. */
export function defaultConfigForType(type: string): Record<string, unknown> {
  switch (type) {
    case "send_notification":
      return { title: "", body: "", severity: "info", role_slugs: [], link: "" };
    case "send_email":
      return { subject: "", body: "", role_slugs: [] };
    case "send_slack":
      return { title: "", body: "" };
    case "log_message":
      return { message: "" };
    case "approval_request":
      return { title: "", role_slugs: [] };
    default:
      return {};
  }
}

// --------------------------------------------------------------------------- //
// Definition normalization
// --------------------------------------------------------------------------- //

export function isConditionLeaf(
  node: WorkflowConditionNode,
): node is WorkflowConditionLeaf {
  return (
    typeof node === "object" &&
    node !== null &&
    "field" in node &&
    !("rules" in node)
  );
}

export function emptyConditions(): WorkflowConditionGroup {
  return { op: "and", rules: [] };
}

export function emptyDefinition(): WorkflowDefinition {
  return {
    trigger: { type: "manual", conditions: null },
    actions: [],
    settings: { max_attempts: 5, stop_on_error: true },
  };
}

/** Normalize a raw definition (possibly partial / from import / AI) into a
 * structure the builder can always rely on. */
export function normalizeDefinitionForClient(
  definition: WorkflowDefinition | null | undefined,
): WorkflowDefinition {
  const base: WorkflowDefinition = definition
    ? (JSON.parse(JSON.stringify(definition)) as WorkflowDefinition)
    : emptyDefinition();

  const rawTrigger = (base.trigger ?? {}) as WorkflowDefinition["trigger"];
  const trigger: WorkflowDefinition["trigger"] = {
    ...rawTrigger,
    type: rawTrigger.type || "manual",
    conditions: normalizeConditions(rawTrigger.conditions),
  };

  const actions: WorkflowAction[] = (base.actions ?? []).map((raw, idx) => {
    const action = (raw ?? {}) as WorkflowAction;
    const id = action.id || `step_${idx + 1}`;
    return {
      id,
      type: action.type || "log_message",
      name: action.name || id,
      config: (action.config as Record<string, unknown>) ?? {},
      conditions: normalizeConditions(action.conditions),
    };
  });

  const settings: WorkflowDefinition["settings"] = {
    max_attempts: 5,
    stop_on_error: true,
    ...(base.settings ?? {}),
  };
  const parsed = Number(settings.max_attempts);
  settings.max_attempts = Number.isFinite(parsed) && parsed > 0 ? parsed : 5;

  return { trigger, actions, settings };
}

function normalizeConditions(
  conditions: WorkflowConditionGroup | null | undefined,
): WorkflowConditionGroup | null {
  if (!conditions || typeof conditions !== "object") return null;
  if (!("rules" in conditions) || !Array.isArray(conditions.rules)) return null;
  if (conditions.rules.length === 0) return null;
  return {
    op: conditions.op === "or" ? "or" : "and",
    rules: conditions.rules,
  };
}

/** Strip empty conditions to null before sending to the API. */
export function serializeDefinition(
  definition: WorkflowDefinition,
): WorkflowDefinition {
  return {
    trigger: {
      ...definition.trigger,
      conditions: emptyToNull(definition.trigger.conditions),
    },
    actions: definition.actions.map((a) => ({
      ...a,
      conditions: emptyToNull(a.conditions),
    })),
    settings: definition.settings,
  };
}

function emptyToNull(
  conditions: WorkflowConditionGroup | null | undefined,
): WorkflowConditionGroup | null {
  if (!conditions || !conditions.rules || conditions.rules.length === 0) {
    return null;
  }
  return conditions;
}

/** Short human summary of a conditions group for the canvas. */
export function conditionsSummary(
  conditions: WorkflowConditionGroup | null | undefined,
): string {
  if (!conditions || !conditions.rules || conditions.rules.length === 0) {
    return "No conditions — always runs.";
  }
  const count = conditions.rules.length;
  const joiner = conditions.op === "or" ? "any of" : "all of";
  return `${count} rule${count === 1 ? "" : "s"} (${joiner}).`;
}
