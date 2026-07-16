"use client";

import type {
  WorkflowCatalogItem,
  WorkflowConditionLeaf,
  WorkflowDefinition,
  WorkflowOperator,
} from "@/lib/api";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import type { WorkflowBuilderActions, WorkflowSelection } from "./builder-types";
import { configFieldsFor, isConditionLeaf } from "./definition-utils";

const selectClass =
  "mt-1 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";
const textareaClass =
  "mt-1 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";

function toDisplay(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function parseList(raw: string): string[] {
  return raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export function PropertiesPanel({
  definition,
  selection,
  actions,
  triggers,
  actionCatalog,
  operators,
  disabled,
}: {
  definition: WorkflowDefinition;
  selection: WorkflowSelection;
  actions: WorkflowBuilderActions;
  triggers: WorkflowCatalogItem[];
  actionCatalog: WorkflowCatalogItem[];
  operators: WorkflowOperator[];
  disabled?: boolean;
}) {
  if (!selection) {
    return (
      <p className="text-sm text-stone-400">
        Select the trigger, conditions, or an action on the canvas to edit it.
      </p>
    );
  }

  if (selection.kind === "trigger") {
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
          Trigger
        </p>
        <div>
          <Label htmlFor="trigger-type">Trigger type</Label>
          <select
            id="trigger-type"
            className={selectClass}
            disabled={disabled}
            value={definition.trigger.type}
            onChange={(e) => actions.setTriggerType(e.target.value)}
          >
            {triggers.map((t) => (
              <option key={t.code} value={t.code}>
                {t.label}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-xs text-stone-400">
            One trigger per workflow. Conditions below decide whether the flow runs.
          </p>
        </div>
      </div>
    );
  }

  if (selection.kind === "conditions") {
    const conditions = definition.trigger.conditions;
    const rules = conditions?.rules ?? [];
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
          Conditions
        </p>
        <div>
          <Label htmlFor="conditions-op">Match</Label>
          <select
            id="conditions-op"
            className={selectClass}
            disabled={disabled}
            value={conditions?.op ?? "and"}
            onChange={(e) => actions.setConditionsOp(e.target.value === "or" ? "or" : "and")}
          >
            <option value="and">All rules (AND)</option>
            <option value="or">Any rule (OR)</option>
          </select>
        </div>

        <div className="space-y-3">
          {rules.length === 0 && (
            <p className="text-xs text-stone-400">
              No conditions — the workflow always runs when triggered.
            </p>
          )}
          {rules.map((rule, index) => {
            if (!isConditionLeaf(rule)) {
              return (
                <p key={index} className="text-xs text-stone-400">
                  Nested condition group (edit via JSON import).
                </p>
              );
            }
            const leaf = rule as WorkflowConditionLeaf;
            return (
              <div
                key={index}
                className="space-y-2 rounded-lg border border-stone-100 p-2.5 dark:border-stone-900"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-stone-500">
                    Rule {index + 1}
                  </span>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    disabled={disabled}
                    onClick={() => actions.removeConditionRule(index)}
                    title="Remove rule"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                  </Button>
                </div>
                <Input
                  aria-label="Field"
                  placeholder="Field (e.g. trigger.status)"
                  disabled={disabled}
                  value={leaf.field ?? ""}
                  onChange={(e) =>
                    actions.updateConditionRule(index, { field: e.target.value })
                  }
                />
                <select
                  aria-label="Comparator"
                  className={selectClass}
                  disabled={disabled}
                  value={leaf.cmp ?? "eq"}
                  onChange={(e) =>
                    actions.updateConditionRule(index, { cmp: e.target.value })
                  }
                >
                  {operators.map((op) => (
                    <option key={op.code} value={op.code}>
                      {op.label}
                    </option>
                  ))}
                </select>
                <Input
                  aria-label="Value"
                  placeholder="Value"
                  disabled={disabled}
                  value={toDisplay(leaf.value)}
                  onChange={(e) =>
                    actions.updateConditionRule(index, { value: e.target.value })
                  }
                />
              </div>
            );
          })}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => actions.addConditionRule()}
          >
            <Plus className="h-3.5 w-3.5" /> Add rule
          </Button>
        </div>
      </div>
    );
  }

  // action
  const action = definition.actions.find((a) => a.id === selection.actionId);
  if (!action) {
    return (
      <p className="text-sm text-stone-400">This action no longer exists.</p>
    );
  }
  const fields = configFieldsFor(action.type);
  const config = action.config ?? {};

  const setConfig = (key: string, value: unknown) =>
    actions.updateActionConfig(action.id, { ...config, [key]: value });

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
        Action
      </p>
      <div>
        <Label htmlFor="action-name">Name</Label>
        <Input
          id="action-name"
          disabled={disabled}
          value={action.name ?? ""}
          placeholder="Step name"
          onChange={(e) => actions.updateAction(action.id, { name: e.target.value })}
        />
      </div>
      <div>
        <Label htmlFor="action-type">Type</Label>
        <select
          id="action-type"
          className={selectClass}
          disabled={disabled}
          value={action.type}
          onChange={(e) => actions.updateAction(action.id, { type: e.target.value })}
        >
          {actionCatalog.map((a) => (
            <option key={a.code} value={a.code}>
              {a.label}
            </option>
          ))}
        </select>
      </div>

      {fields.length > 0 && (
        <div className="space-y-3 border-t border-stone-100 pt-3 dark:border-stone-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
            Configuration
          </p>
          {fields.map((field) => {
            const value = config[field.key];
            if (field.kind === "textarea") {
              return (
                <div key={field.key}>
                  <Label htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                  <textarea
                    id={`cfg-${field.key}`}
                    className={textareaClass}
                    rows={3}
                    disabled={disabled}
                    placeholder={field.placeholder}
                    value={toDisplay(value)}
                    onChange={(e) => setConfig(field.key, e.target.value)}
                  />
                  {field.help && (
                    <p className="mt-1 text-xs text-stone-400">{field.help}</p>
                  )}
                </div>
              );
            }
            if (field.kind === "select") {
              return (
                <div key={field.key}>
                  <Label htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                  <select
                    id={`cfg-${field.key}`}
                    className={selectClass}
                    disabled={disabled}
                    value={toDisplay(value)}
                    onChange={(e) => setConfig(field.key, e.target.value)}
                  >
                    <option value="">—</option>
                    {(field.options ?? []).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              );
            }
            if (field.kind === "list") {
              return (
                <div key={field.key}>
                  <Label htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                  <Input
                    id={`cfg-${field.key}`}
                    disabled={disabled}
                    placeholder={field.placeholder}
                    value={toDisplay(value)}
                    onChange={(e) => setConfig(field.key, parseList(e.target.value))}
                  />
                  {field.help && (
                    <p className="mt-1 text-xs text-stone-400">{field.help}</p>
                  )}
                </div>
              );
            }
            return (
              <div key={field.key}>
                <Label htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                <Input
                  id={`cfg-${field.key}`}
                  type={field.kind === "number" ? "number" : "text"}
                  disabled={disabled}
                  placeholder={field.placeholder}
                  value={toDisplay(value)}
                  onChange={(e) =>
                    setConfig(
                      field.key,
                      field.kind === "number"
                        ? e.target.value === ""
                          ? ""
                          : Number(e.target.value)
                        : e.target.value,
                    )
                  }
                />
                {field.help && (
                  <p className="mt-1 text-xs text-stone-400">{field.help}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
