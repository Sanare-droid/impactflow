"use client";

import { useMemo } from "react";
import type { FieldTypeInfo, SurveyField, SurveySchema } from "@/lib/api";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import type { BuilderActions, BuilderSelection } from "./builder-types";
import { CHOICE_FIELD_TYPES, NUMERIC_FIELD_TYPES, TEXT_VALIDATION_TYPES, iterFields } from "./schema-utils";

const selectClass =
  "mt-1 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";

function findField(schema: SurveySchema, pageId: string, sectionId: string, fieldId: string): SurveyField | null {
  for (const page of schema.pages || []) {
    if (page.id !== pageId) continue;
    for (const section of page.sections || []) {
      if (section.id !== sectionId) continue;
      for (const field of section.fields || []) {
        if (field.id === fieldId) return field;
      }
    }
  }
  return null;
}

export function PropertiesPanel({
  schema,
  selection,
  actions,
  fieldTypes,
  disabled,
}: {
  schema: SurveySchema;
  selection: BuilderSelection;
  actions: BuilderActions;
  fieldTypes: FieldTypeInfo[];
  disabled?: boolean;
}) {
  const allFields = useMemo(() => iterFields(schema), [schema]);

  if (!selection) {
    return (
      <p className="text-sm text-stone-400">
        Select a field, section, or page on the canvas to edit its properties.
      </p>
    );
  }

  if (selection.kind === "page") {
    const page = (schema.pages || []).find((p) => p.id === selection.pageId);
    if (!page) return null;
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">Page</p>
        <div>
          <Label htmlFor="page-title">Title</Label>
          <Input
            id="page-title"
            disabled={disabled}
            value={page.title || ""}
            onChange={(e) => actions.updatePage(page.id, { title: e.target.value })}
          />
        </div>
      </div>
    );
  }

  if (selection.kind === "section") {
    const page = (schema.pages || []).find((p) => p.id === selection.pageId);
    const section = page?.sections.find((s) => s.id === selection.sectionId);
    if (!page || !section) return null;
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">Section</p>
        <div>
          <Label htmlFor="section-title">Title</Label>
          <Input
            id="section-title"
            disabled={disabled}
            value={section.title || ""}
            onChange={(e) => actions.updateSection(page.id, section.id, { title: e.target.value })}
          />
        </div>
      </div>
    );
  }

  // field
  const field = findField(schema, selection.pageId, selection.sectionId, selection.fieldId);
  if (!field) return null;

  const patch = (p: Partial<SurveyField>) =>
    actions.updateField(selection.pageId, selection.sectionId, selection.fieldId, p);

  const isChoice = CHOICE_FIELD_TYPES.has(field.type);
  const isNumeric = NUMERIC_FIELD_TYPES.has(field.type);
  const isTextValidated = TEXT_VALIDATION_TYPES.has(field.type);
  const otherFields = allFields.filter((f) => f.id !== field.id && f.type !== "section_header");

  return (
    <div className="space-y-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">Field</p>

      <div>
        <Label htmlFor="field-label">Label</Label>
        <Input
          id="field-label"
          disabled={disabled}
          value={field.label || ""}
          onChange={(e) => patch({ label: e.target.value })}
        />
      </div>

      <div>
        <Label htmlFor="field-type">Type</Label>
        <select
          id="field-type"
          className={selectClass}
          disabled={disabled}
          value={field.type}
          onChange={(e) => patch({ type: e.target.value })}
        >
          {fieldTypes.map((ft) => (
            <option key={ft.code} value={ft.code}>
              {ft.label}
            </option>
          ))}
        </select>
      </div>

      {field.type !== "section_header" && (
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
            <input
              type="checkbox"
              disabled={disabled}
              checked={Boolean(field.required)}
              onChange={(e) => patch({ required: e.target.checked })}
            />
            Required
          </label>
          <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
            <input
              type="checkbox"
              disabled={disabled}
              checked={Boolean(field.hidden)}
              onChange={(e) => patch({ hidden: e.target.checked })}
            />
            Hidden
          </label>
          <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
            <input
              type="checkbox"
              disabled={disabled}
              checked={Boolean(field.read_only)}
              onChange={(e) => patch({ read_only: e.target.checked })}
            />
            Read only
          </label>
        </div>
      )}

      {field.type !== "section_header" && (
        <>
          <div>
            <Label htmlFor="field-placeholder">Placeholder</Label>
            <Input
              id="field-placeholder"
              disabled={disabled}
              value={field.placeholder || ""}
              onChange={(e) => patch({ placeholder: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="field-help">Help text</Label>
            <textarea
              id="field-help"
              disabled={disabled}
              className={selectClass}
              rows={2}
              value={field.help_text || ""}
              onChange={(e) => patch({ help_text: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="field-default">Default value</Label>
            <Input
              id="field-default"
              disabled={disabled}
              value={(field.default as string) ?? ""}
              onChange={(e) => patch({ default: e.target.value || undefined })}
            />
          </div>
        </>
      )}

      {isChoice && (
        <div>
          <Label>Options</Label>
          <div className="space-y-2">
            {(field.options || []).map((opt, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Input
                  disabled={disabled}
                  value={opt.label}
                  placeholder="Label"
                  onChange={(e) => {
                    const options = [...(field.options || [])];
                    options[idx] = { ...options[idx], label: e.target.value };
                    patch({ options });
                  }}
                />
                <Input
                  disabled={disabled}
                  value={opt.value}
                  placeholder="Value"
                  onChange={(e) => {
                    const options = [...(field.options || [])];
                    options[idx] = { ...options[idx], value: e.target.value };
                    patch({ options });
                  }}
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="h-9 w-9 shrink-0"
                  disabled={disabled}
                  onClick={() => {
                    const options = (field.options || []).filter((_, i) => i !== idx);
                    patch({ options });
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={disabled}
              onClick={() => {
                const n = (field.options || []).length + 1;
                patch({
                  options: [...(field.options || []), { value: `option_${n}`, label: `Option ${n}` }],
                });
              }}
            >
              <Plus className="h-3.5 w-3.5" /> Add option
            </Button>
          </div>
        </div>
      )}

      {isNumeric && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="field-min">Min</Label>
            <Input
              id="field-min"
              type="number"
              disabled={disabled}
              value={field.validation?.min ?? ""}
              onChange={(e) =>
                patch({
                  validation: {
                    ...field.validation,
                    min: e.target.value === "" ? undefined : Number(e.target.value),
                  },
                })
              }
            />
          </div>
          <div>
            <Label htmlFor="field-max">Max</Label>
            <Input
              id="field-max"
              type="number"
              disabled={disabled}
              value={field.validation?.max ?? ""}
              onChange={(e) =>
                patch({
                  validation: {
                    ...field.validation,
                    max: e.target.value === "" ? undefined : Number(e.target.value),
                  },
                })
              }
            />
          </div>
        </div>
      )}

      {isTextValidated && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="field-minlen">Min length</Label>
              <Input
                id="field-minlen"
                type="number"
                disabled={disabled}
                value={field.validation?.min_length ?? ""}
                onChange={(e) =>
                  patch({
                    validation: {
                      ...field.validation,
                      min_length: e.target.value === "" ? undefined : Number(e.target.value),
                    },
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="field-maxlen">Max length</Label>
              <Input
                id="field-maxlen"
                type="number"
                disabled={disabled}
                value={field.validation?.max_length ?? ""}
                onChange={(e) =>
                  patch({
                    validation: {
                      ...field.validation,
                      max_length: e.target.value === "" ? undefined : Number(e.target.value),
                    },
                  })
                }
              />
            </div>
          </div>
          <div>
            <Label htmlFor="field-regex">Validation regex</Label>
            <Input
              id="field-regex"
              disabled={disabled}
              value={field.validation?.regex ?? ""}
              onChange={(e) =>
                patch({ validation: { ...field.validation, regex: e.target.value || undefined } })
              }
            />
          </div>
        </div>
      )}

      {field.type !== "section_header" && (
        <div className="space-y-2 rounded-lg border border-stone-100 p-3 dark:border-stone-900">
          <Label>Show only if…</Label>
          {otherFields.length === 0 ? (
            <p className="text-xs text-stone-400">Add more fields to set conditional logic.</p>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              <select
                className={selectClass}
                disabled={disabled}
                value={field.logic?.show_if?.field || ""}
                onChange={(e) => {
                  if (!e.target.value) {
                    patch({ logic: undefined });
                    return;
                  }
                  patch({
                    logic: {
                      show_if: {
                        field: e.target.value,
                        op: field.logic?.show_if?.op || "eq",
                        value: field.logic?.show_if?.value ?? "",
                      },
                    },
                  });
                }}
              >
                <option value="">No condition</option>
                {otherFields.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label || f.id}
                  </option>
                ))}
              </select>
              <select
                className={selectClass}
                disabled={disabled || !field.logic?.show_if}
                value={field.logic?.show_if?.op || "eq"}
                onChange={(e) =>
                  patch({
                    logic: {
                      show_if: {
                        field: field.logic?.show_if?.field || "",
                        op: e.target.value as "eq" | "neq" | "in" | "not_in" | "truthy" | "falsy",
                        value: field.logic?.show_if?.value ?? "",
                      },
                    },
                  })
                }
              >
                <option value="eq">equals</option>
                <option value="neq">not equals</option>
                <option value="in">is one of</option>
                <option value="not_in">is not one of</option>
                <option value="truthy">is truthy</option>
                <option value="falsy">is falsy</option>
              </select>
              <Input
                disabled={disabled || !field.logic?.show_if || ["truthy", "falsy"].includes(field.logic?.show_if?.op || "")}
                placeholder="Value"
                value={(field.logic?.show_if?.value as string) ?? ""}
                onChange={(e) =>
                  patch({
                    logic: {
                      show_if: {
                        field: field.logic?.show_if?.field || "",
                        op: field.logic?.show_if?.op || "eq",
                        value: e.target.value,
                      },
                    },
                  })
                }
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}