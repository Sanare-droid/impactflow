"use client";

import type { WorkflowCatalogItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CATEGORY_LABELS } from "./definition-utils";

function groupByCategory(items: WorkflowCatalogItem[]) {
  const grouped = new Map<string, WorkflowCatalogItem[]>();
  for (const item of items) {
    const key = item.category || "other";
    const list = grouped.get(key) || [];
    list.push(item);
    grouped.set(key, list);
  }
  return grouped;
}

function PaletteButton({
  label,
  suffix,
  disabled,
  onClick,
}: {
  label: string;
  suffix: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex items-center justify-between rounded-lg border border-stone-200 bg-white px-3 py-2 text-left text-sm text-stone-700 transition-colors hover:border-teal-300 hover:bg-teal-50/60 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-800 dark:bg-stone-950 dark:text-stone-300 dark:hover:border-teal-800 dark:hover:bg-teal-950/40",
      )}
    >
      <span className="min-w-0 truncate">{label}</span>
      <span className="ml-2 shrink-0 text-stone-300 dark:text-stone-600">
        {suffix}
      </span>
    </button>
  );
}

export function StepPalette({
  triggers,
  actions,
  onSetTrigger,
  onAddAction,
  disabled,
}: {
  triggers: WorkflowCatalogItem[];
  actions: WorkflowCatalogItem[];
  onSetTrigger: (code: string) => void;
  onAddAction: (code: string) => void;
  disabled?: boolean;
}) {
  const triggerGroups = groupByCategory(triggers);
  const actionGroups = groupByCategory(actions);

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">
          Triggers
        </p>
        <p className="mb-3 text-xs text-stone-400">
          Sets the workflow trigger (one per workflow).
        </p>
        <div className="space-y-4">
          {Array.from(triggerGroups.entries()).map(([category, items]) => (
            <div key={category}>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                {CATEGORY_LABELS[category] || category}
              </p>
              <div className="flex flex-col gap-1.5">
                {items.map((item) => (
                  <PaletteButton
                    key={item.code}
                    label={item.label}
                    suffix="set"
                    disabled={disabled}
                    onClick={() => onSetTrigger(item.code)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">
          Actions
        </p>
        <p className="mb-3 text-xs text-stone-400">Adds a step to the flow.</p>
        <div className="space-y-4">
          {Array.from(actionGroups.entries()).map(([category, items]) => (
            <div key={category}>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                {CATEGORY_LABELS[category] || category}
              </p>
              <div className="flex flex-col gap-1.5">
                {items.map((item) => (
                  <PaletteButton
                    key={item.code}
                    label={item.label}
                    suffix="+"
                    disabled={disabled}
                    onClick={() => onAddAction(item.code)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
