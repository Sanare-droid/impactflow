/** Helpers for rendering a survey schema (v1 flat `fields` or v2 `pages/sections/fields`). */
import type { SurveyField } from "@/lib/api";

const SUPPORTED_TYPES = new Set([
  "text",
  "long_text",
  "textarea",
  "number",
  "dropdown",
  "select",
  "radio",
  "boolean",
  "date",
  "email",
  "phone",
]);

/** Canonicalize server field type aliases to what the capture form knows how to render. */
export function normalizeFieldType(type: string): string {
  const t = (type || "text").toLowerCase();
  if (t === "textarea") return "long_text";
  if (t === "select") return "dropdown";
  return t;
}

export function isSupportedFieldType(type: string): boolean {
  return SUPPORTED_TYPES.has((type || "").toLowerCase());
}

/** Flatten a survey's schema (pages/sections/fields or legacy fields) into a single list. */
export function flattenSurveyFields(schema: Record<string, unknown> | null | undefined): SurveyField[] {
  if (!schema) return [];
  const fields: SurveyField[] = [];
  const pages = Array.isArray(schema.pages) ? (schema.pages as Record<string, unknown>[]) : null;
  if (pages) {
    for (const page of pages) {
      const sections = Array.isArray(page.sections)
        ? (page.sections as Record<string, unknown>[])
        : [];
      for (const section of sections) {
        const sectionFields = Array.isArray(section.fields)
          ? (section.fields as SurveyField[])
          : [];
        fields.push(...sectionFields);
      }
    }
  }
  if (fields.length === 0 && Array.isArray(schema.fields)) {
    fields.push(...(schema.fields as SurveyField[]));
  }
  return fields;
}

/** Client-side required-field validation. Returns a map of field id -> error message. */
export function validateAnswers(
  fields: SurveyField[],
  answers: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    if (!field.required) continue;
    const value = answers[field.id];
    const isEmpty =
      value === undefined ||
      value === null ||
      value === "" ||
      (typeof value === "string" && value.trim() === "");
    if (isEmpty) {
      errors[field.id] = `${field.label} is required`;
    }
    if (normalizeFieldType(field.type) === "email" && typeof value === "string" && value.trim()) {
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())) {
        errors[field.id] = "Enter a valid email";
      }
    }
  }
  return errors;
}
