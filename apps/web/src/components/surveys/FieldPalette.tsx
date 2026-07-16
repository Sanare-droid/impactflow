"use client";

import type { FieldTypeInfo } from "@/lib/api";
import { FIELD_TYPE_CATEGORY_LABELS } from "./schema-utils";
import { cn } from "@/lib/utils";

export function FieldPalette({
  fieldTypes,
  onAdd,
  disabled,
}: {
  fieldTypes: FieldTypeInfo[];
  onAdd: (type: string) => void;
  disabled?: boolean;
}) {
  const grouped = new Map<string, FieldTypeInfo[]>();
  for (const ft of fieldTypes) {
    const list = grouped.get(ft.category) || [];
    list.push(ft);
    grouped.set(ft.category, list);
  }

  return (
    <div className="space-y-5">
      {Array.from(grouped.entries()).map(([category, items]) => (
        <div key={category}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-400">
            {FIELD_TYPE_CATEGORY_LABELS[category] || category}
          </p>
          <div className="flex flex-col gap-1.5">
            {items.map((ft) => (
              <button
                key={ft.code}
                type="button"
                disabled={disabled}
                onClick={() => onAdd(ft.code)}
                className={cn(
                  "flex items-center justify-between rounded-lg border border-stone-200 bg-white px-3 py-2 text-left text-sm text-stone-700 transition-colors hover:border-teal-300 hover:bg-teal-50/60 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-800 dark:bg-stone-950 dark:text-stone-300 dark:hover:border-teal-800 dark:hover:bg-teal-950/40",
                )}
              >
                {ft.label}
                <span className="text-stone-300 dark:text-stone-600">+</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
