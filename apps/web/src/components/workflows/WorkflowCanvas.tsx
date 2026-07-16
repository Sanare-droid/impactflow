"use client";

import { ArrowDown, ArrowUp, Trash2, Zap } from "lucide-react";
import type {
  WorkflowCatalogItem,
  WorkflowDefinition,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { WorkflowBuilderActions, WorkflowSelection } from "./builder-types";
import { catalogLabel, conditionsSummary } from "./definition-utils";

export function WorkflowCanvas({
  definition,
  selection,
  actions,
  triggers,
  actionCatalog,
  disabled,
}: {
  definition: WorkflowDefinition;
  selection: WorkflowSelection;
  actions: WorkflowBuilderActions;
  triggers: WorkflowCatalogItem[];
  actionCatalog: WorkflowCatalogItem[];
  disabled?: boolean;
}) {
  const triggerSelected = selection?.kind === "trigger";
  const conditionsSelected = selection?.kind === "conditions";
  const conditions = definition.trigger.conditions;

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => actions.select({ kind: "trigger" })}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-left transition-colors hover:border-teal-300 dark:border-stone-800 dark:bg-stone-900/60 dark:hover:border-teal-800",
          triggerSelected && "border-teal-400 bg-teal-50/70 ring-1 ring-teal-300/50 dark:bg-teal-950/30",
        )}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-700 text-white dark:bg-teal-600">
          <Zap className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">
            Trigger
          </span>
          <span className="block truncate text-sm font-medium text-stone-800 dark:text-stone-100">
            {catalogLabel(triggers, definition.trigger.type)}
          </span>
        </span>
      </button>

      <div className="flex justify-center">
        <span className="h-4 w-px bg-stone-300 dark:bg-stone-700" />
      </div>

      <button
        type="button"
        onClick={() => actions.select({ kind: "conditions" })}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl border border-dashed border-stone-200 px-4 py-2.5 text-left transition-colors hover:border-teal-300 dark:border-stone-800 dark:hover:border-teal-800",
          conditionsSelected && "border-teal-400 bg-teal-50/60 ring-1 ring-teal-300/50 dark:bg-teal-950/30",
        )}
      >
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-stone-400">
            Conditions
          </span>
          <span className="block truncate text-sm text-stone-600 dark:text-stone-300">
            {conditionsSummary(conditions)}
          </span>
        </span>
      </button>

      <div className="flex justify-center">
        <span className="h-4 w-px bg-stone-300 dark:bg-stone-700" />
      </div>

      <div className="space-y-2">
        {definition.actions.length === 0 && (
          <p className="rounded-xl border border-dashed border-stone-200 px-4 py-6 text-center text-xs text-stone-400 dark:border-stone-800">
            No actions yet — add a step from the palette on the left.
          </p>
        )}
        {definition.actions.map((action, idx) => {
          const active = selection?.kind === "action" && selection.actionId === action.id;
          return (
            <div key={action.id}>
              {idx > 0 && (
                <div className="flex justify-center py-1">
                  <span className="h-3 w-px bg-stone-300 dark:bg-stone-700" />
                </div>
              )}
              <button
                type="button"
                onClick={() => actions.select({ kind: "action", actionId: action.id })}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl border border-stone-200 bg-white px-4 py-3 text-left transition-colors hover:border-teal-300 dark:border-stone-800 dark:bg-stone-950 dark:hover:border-teal-800",
                  active && "border-teal-400 bg-teal-50/60 ring-1 ring-teal-300/50 dark:bg-teal-950/30",
                )}
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-xs font-semibold text-stone-500 dark:bg-stone-800 dark:text-stone-400">
                  {idx + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-stone-800 dark:text-stone-100">
                    {action.name || catalogLabel(actionCatalog, action.type)}
                  </span>
                  <span className="block truncate text-xs text-stone-400">
                    {catalogLabel(actionCatalog, action.type)}
                    {action.conditions && action.conditions.rules.length > 0 ? " · conditional" : ""}
                  </span>
                </span>
                <span
                  className="flex shrink-0 items-center gap-0.5"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    disabled={disabled || idx === 0}
                    onClick={() => actions.moveAction(action.id, -1)}
                    title="Move up"
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    disabled={disabled || idx === definition.actions.length - 1}
                    onClick={() => actions.moveAction(action.id, 1)}
                    title="Move down"
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    disabled={disabled}
                    onClick={() => actions.removeAction(action.id)}
                    title="Delete step"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                  </Button>
                </span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
