import type { SurveyField, SurveyPage, SurveySchema, FieldTypeInfo } from "@/lib/api";

let idCounter = 0;

/** Short client-side unique id — good enough for local builder state; the API
 * re-normalizes ids on save so collisions across sessions are not a concern. */
export function newId(prefix: string): string {
  idCounter += 1;
  return `${prefix}_${Date.now().toString(36)}${idCounter.toString(36)}`;
}

/** Local fallback catalog, used until /surveys/field-types resolves (or if it fails). */
export const FALLBACK_FIELD_TYPES: FieldTypeInfo[] = [
  { code: "text", label: "Text", category: "text" },
  { code: "long_text", label: "Long text", category: "text" },
  { code: "rich_text", label: "Rich text", category: "text" },
  { code: "number", label: "Number", category: "numeric" },
  { code: "decimal", label: "Decimal", category: "numeric" },
  { code: "currency", label: "Currency", category: "numeric" },
  { code: "date", label: "Date", category: "datetime" },
  { code: "time", label: "Time", category: "datetime" },
  { code: "datetime", label: "Date & time", category: "datetime" },
  { code: "email", label: "Email", category: "text" },
  { code: "phone", label: "Phone", category: "text" },
  { code: "url", label: "URL", category: "text" },
  { code: "boolean", label: "Yes / No", category: "choice" },
  { code: "checkbox", label: "Checkbox", category: "choice" },
  { code: "radio", label: "Radio", category: "choice" },
  { code: "dropdown", label: "Dropdown", category: "choice" },
  { code: "multi_select", label: "Multi select", category: "choice" },
  { code: "gps", label: "GPS", category: "media" },
  { code: "image", label: "Image", category: "media" },
  { code: "video", label: "Video", category: "media" },
  { code: "audio", label: "Audio", category: "media" },
  { code: "file", label: "File upload", category: "media" },
  { code: "signature", label: "Signature", category: "media" },
  { code: "qr_code", label: "QR code", category: "scan" },
  { code: "barcode", label: "Barcode", category: "scan" },
  { code: "matrix", label: "Matrix", category: "advanced" },
  { code: "rating", label: "Rating", category: "advanced" },
  { code: "slider", label: "Slider", category: "advanced" },
  { code: "repeat_group", label: "Repeat group", category: "advanced" },
  { code: "section_header", label: "Section header", category: "layout" },
];

export const FIELD_TYPE_CATEGORY_LABELS: Record<string, string> = {
  text: "Text",
  numeric: "Numeric",
  datetime: "Date & time",
  choice: "Choice",
  media: "Media",
  scan: "Scan",
  advanced: "Advanced",
  layout: "Layout",
};

export const CHOICE_FIELD_TYPES = new Set(["radio", "dropdown", "multi_select"]);
export const NUMERIC_FIELD_TYPES = new Set(["number", "decimal", "currency", "rating", "slider"]);
export const TEXT_VALIDATION_TYPES = new Set([
  "text",
  "long_text",
  "rich_text",
  "phone",
  "qr_code",
  "barcode",
]);

/** Normalize a raw survey schema (pages/sections OR legacy flat `fields`) into a
 * pages/sections structure the builder + renderer can always rely on. Mirrors
 * app.services.form_schema.normalize_schema on the API. */
export function normalizeSchemaForClient(schema: SurveySchema | null | undefined): SurveySchema {
  const base: SurveySchema = schema ? JSON.parse(JSON.stringify(schema)) : {};

  if (!base.pages && base.fields && base.fields.length) {
    const fields = base.fields.map((f) => ({ ...f, id: f.id || newId("f") }));
    return {
      schema_version: 2,
      settings: {
        progress_bar: true,
        allow_draft: true,
        auto_save: true,
        randomize_questions: false,
        anonymous: false,
        ...(base.settings || {}),
      },
      pages: [
        {
          id: newId("page"),
          title: "Page 1",
          sections: [{ id: newId("sec"), title: "Questions", fields }],
        },
      ],
    };
  }

  const pages: SurveyPage[] = (base.pages || []).map((page) => ({
    ...page,
    id: page.id || newId("page"),
    sections: (page.sections || []).map((section) => ({
      ...section,
      id: section.id || newId("sec"),
      fields: (section.fields || []).map((field) => ({ ...field, id: field.id || newId("f") })),
    })),
  }));

  if (pages.length === 0) {
    pages.push({ id: newId("page"), title: "Page 1", sections: [{ id: newId("sec"), title: "Questions", fields: [] }] });
  }

  return {
    schema_version: base.schema_version ?? 2,
    settings: {
      progress_bar: true,
      allow_draft: true,
      auto_save: true,
      randomize_questions: false,
      anonymous: false,
      ...(base.settings || {}),
    },
    pages,
  };
}

export function iterFields(schema: SurveySchema): SurveyField[] {
  const out: SurveyField[] = [];
  for (const page of schema.pages || []) {
    for (const section of page.sections || []) {
      for (const field of section.fields || []) {
        out.push(field);
      }
    }
  }
  return out;
}

export function evaluateShowIf(
  answers: Record<string, unknown>,
  field: SurveyField,
): boolean {
  const showIf = field.logic?.show_if;
  if (!showIf) return true;
  const actual = answers[showIf.field];
  const expected = showIf.value;
  switch (showIf.op) {
    case "eq":
      return actual === expected;
    case "neq":
      return actual !== expected;
    case "in":
      return Array.isArray(expected) ? expected.includes(actual) : false;
    case "not_in":
      return Array.isArray(expected) ? !expected.includes(actual) : true;
    case "truthy":
      return Boolean(actual);
    case "falsy":
      return !actual;
    default:
      return true;
  }
}

export function emptySchema(): SurveySchema {
  return {
    schema_version: 2,
    settings: {
      progress_bar: true,
      allow_draft: true,
      auto_save: true,
      randomize_questions: false,
      anonymous: false,
    },
    pages: [
      {
        id: newId("page"),
        title: "Page 1",
        sections: [{ id: newId("sec"), title: "Questions", fields: [] }],
      },
    ],
  };
}

export function defaultFieldForType(type: string): SurveyField {
  const field: SurveyField = {
    id: newId("f"),
    type,
    label: FALLBACK_FIELD_TYPES.find((t) => t.code === type)?.label || "New field",
    required: false,
  };
  if (CHOICE_FIELD_TYPES.has(type)) {
    field.options = [
      { value: "option_1", label: "Option 1" },
      { value: "option_2", label: "Option 2" },
    ];
  }
  if (type === "section_header") {
    field.label = "Section header";
  }
  return field;
}
