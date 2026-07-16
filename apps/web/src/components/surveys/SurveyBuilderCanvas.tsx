"use client";

import type { SurveySchema } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import type { BuilderActions, BuilderSelection } from "./builder-types";
import { FALLBACK_FIELD_TYPES } from "./schema-utils";

function typeLabel(type: string) {
  return FALLBACK_FIELD_TYPES.find((t) => t.code === type)?.label || type;
}

export function SurveyBuilderCanvas({
  schema,
  selection,
  actions,
  disabled,
}: {
  schema: SurveySchema;
  selection: BuilderSelection;
  actions: BuilderActions;
  disabled?: boolean;
}) {
  const pages = schema.pages || [];

  return (
    <div className="space-y-6">
      {pages.map((page, pageIdx) => (
        <div
          key={page.id}
          className={cn(
            "rounded-xl border border-stone-200 dark:border-stone-800",
            selection?.kind === "page" && selection.pageId === page.id && "border-teal-400 ring-1 ring-teal-300/50",
          )}
        >
          <div className="flex items-center justify-between gap-2 border-b border-stone-100 bg-stone-50/70 px-4 py-2.5 dark:border-stone-900 dark:bg-stone-900/40">
            <button
              type="button"
              className="flex-1 text-left text-sm font-semibold text-stone-800 dark:text-stone-100"
              onClick={() => actions.select({ kind: "page", pageId: page.id })}
            >
              {page.title || `Page ${pageIdx + 1}`}
            </button>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                disabled={disabled || pageIdx === 0}
                onClick={() => actions.movePage(page.id, -1)}
                title="Move page up"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                disabled={disabled || pageIdx === pages.length - 1}
                onClick={() => actions.movePage(page.id, 1)}
                title="Move page down"
              >
                <ArrowDown className="h-3.5 w-3.5" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-7 w-7"
                disabled={disabled || pages.length <= 1}
                onClick={() => actions.deletePage(page.id)}
                title="Delete page"
              >
                <Trash2 className="h-3.5 w-3.5 text-rose-500" />
              </Button>
            </div>
          </div>

          <div className="space-y-4 p-4">
            {(page.sections || []).map((section, sectionIdx) => (
              <div
                key={section.id}
                className={cn(
                  "rounded-lg border border-stone-100 dark:border-stone-900",
                  selection?.kind === "section" &&
                    selection.sectionId === section.id &&
                    "border-teal-400 ring-1 ring-teal-300/50",
                )}
              >
                <div className="flex items-center justify-between gap-2 border-b border-stone-100 px-3 py-2 dark:border-stone-900">
                  <button
                    type="button"
                    className="flex-1 text-left text-sm font-medium text-stone-600 dark:text-stone-300"
                    onClick={() => actions.select({ kind: "section", pageId: page.id, sectionId: section.id })}
                  >
                    {section.title || "Untitled section"}
                  </button>
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      disabled={disabled || sectionIdx === 0}
                      onClick={() => actions.moveSection(page.id, section.id, -1)}
                      title="Move section up"
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      disabled={disabled || sectionIdx === (page.sections || []).length - 1}
                      onClick={() => actions.moveSection(page.id, section.id, 1)}
                      title="Move section down"
                    >
                      <ArrowDown className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      disabled={disabled || (page.sections || []).length <= 1}
                      onClick={() => actions.deleteSection(page.id, section.id)}
                      title="Delete section"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-1.5 p-2.5">
                  {(section.fields || []).length === 0 && (
                    <p className="px-2 py-3 text-center text-xs text-stone-400">
                      No fields yet — pick a field type from the palette to add one here.
                    </p>
                  )}
                  {(section.fields || []).map((field, fieldIdx) => (
                    <button
                      key={field.id}
                      type="button"
                      onClick={() =>
                        actions.select({ kind: "field", pageId: page.id, sectionId: section.id, fieldId: field.id })
                      }
                      className={cn(
                        "flex w-full items-center justify-between gap-2 rounded-lg border border-transparent bg-stone-50 px-3 py-2 text-left text-sm transition-colors hover:border-teal-200 dark:bg-stone-900/60 dark:hover:border-teal-800",
                        selection?.kind === "field" &&
                          selection.fieldId === field.id &&
                          "border-teal-400 bg-teal-50/60 dark:bg-teal-950/30",
                      )}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-stone-800 dark:text-stone-100">
                          {field.label || "(untitled)"}
                          {field.required ? " *" : ""}
                        </span>
                        <span className="text-xs text-stone-400">
                          {typeLabel(field.type)}
                          {field.hidden ? " · hidden" : ""}
                          {field.read_only ? " · read-only" : ""}
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          disabled={disabled || fieldIdx === 0}
                          onClick={() => actions.moveField(page.id, section.id, field.id, -1)}
                          title="Move up"
                        >
                          <ArrowUp className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          disabled={disabled || fieldIdx === (section.fields || []).length - 1}
                          onClick={() => actions.moveField(page.id, section.id, field.id, 1)}
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
                          onClick={() => actions.deleteField(page.id, section.id, field.id)}
                          title="Delete field"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                        </Button>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={disabled}
              onClick={() => actions.addSection(page.id)}
            >
              <Plus className="h-3.5 w-3.5" /> Add section
            </Button>
          </div>
        </div>
      ))}

      <Button type="button" variant="secondary" size="sm" disabled={disabled} onClick={() => actions.addPage()}>
        <Plus className="h-3.5 w-3.5" /> Add page
      </Button>
    </div>
  );
}
