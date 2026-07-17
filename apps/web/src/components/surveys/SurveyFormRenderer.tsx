"use client";

import type { SurveyField, SurveyPage } from "@/lib/api";
import { Label } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { evaluateShowIf } from "./schema-utils";

type Props = {
  page: SurveyPage;
  answers: Record<string, unknown>;
  onChange: (fieldId: string, value: unknown) => void;
  readOnly?: boolean;
  errors?: Record<string, string>;
};

const inputClass =
  "flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm transition-colors placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";

const textareaClass = cn(inputClass, "h-24 resize-y py-2");

function FieldWidget({
  field,
  value,
  onChange,
  readOnly,
}: {
  field: SurveyField;
  value: unknown;
  onChange: (value: unknown) => void;
  readOnly?: boolean;
}) {
  const type = field.type;
  const disabled = readOnly || field.read_only;

  if (type === "section_header") {
    return null;
  }

  if (type === "long_text" || type === "rich_text") {
    return (
      <textarea
        id={field.id}
        className={textareaClass}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "number") {
    return (
      <input
        id={field.id}
        type="number"
        step="1"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder}
        min={field.validation?.min}
        max={field.validation?.max}
        value={(value as string | number) ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
      />
    );
  }

  if (type === "decimal" || type === "currency") {
    return (
      <div className="relative">
        {type === "currency" && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-stone-400">
            $
          </span>
        )}
        <input
          id={field.id}
          type="number"
          step="0.01"
          className={cn(inputClass, type === "currency" && "pl-7")}
          disabled={disabled}
          required={field.required}
          placeholder={field.placeholder}
          min={field.validation?.min}
          max={field.validation?.max}
          value={(value as string | number) ?? ""}
          onChange={(e) => onChange(e.target.value === "" ? undefined : e.target.value)}
        />
      </div>
    );
  }

  if (type === "date") {
    return (
      <input
        id={field.id}
        type="date"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "time") {
    return (
      <input
        id={field.id}
        type="time"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "datetime") {
    return (
      <input
        id={field.id}
        type="datetime-local"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "email") {
    return (
      <input
        id={field.id}
        type="email"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "phone") {
    return (
      <input
        id={field.id}
        type="tel"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "url") {
    return (
      <input
        id={field.id}
        type="url"
        className={inputClass}
        disabled={disabled}
        required={field.required}
        placeholder={field.placeholder || "https://"}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "boolean" || type === "checkbox") {
    return (
      <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
        <input
          id={field.id}
          type="checkbox"
          className="h-4 w-4 rounded border-stone-300 text-teal-700 focus:ring-teal-500/40 dark:border-stone-700"
          disabled={disabled}
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        {field.placeholder || "Yes"}
      </label>
    );
  }

  if (type === "radio") {
    return (
      <div className="flex flex-col gap-2">
        {(field.options || []).map((opt) => (
          <label
            key={opt.value}
            className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300"
          >
            <input
              type="radio"
              name={field.id}
              className="h-4 w-4 border-stone-300 text-teal-700 focus:ring-teal-500/40"
              disabled={disabled}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            {opt.label}
          </label>
        ))}
      </div>
    );
  }

  if (type === "dropdown") {
    return (
      <select
        id={field.id}
        className={inputClass}
        disabled={disabled}
        required={field.required}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select…</option>
        {(field.options || []).map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }

  if (type === "multi_select") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="flex flex-col gap-2">
        {(field.options || []).map((opt) => (
          <label
            key={opt.value}
            className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300"
          >
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-stone-300 text-teal-700 focus:ring-teal-500/40"
              disabled={disabled}
              checked={selected.includes(opt.value)}
              onChange={(e) => {
                if (e.target.checked) onChange([...selected, opt.value]);
                else onChange(selected.filter((v) => v !== opt.value));
              }}
            />
            {opt.label}
          </label>
        ))}
      </div>
    );
  }

  if (type === "rating") {
    const current = Number(value) || 0;
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            disabled={disabled}
            onClick={() => onChange(n)}
            className={cn(
              "h-9 w-9 rounded-lg border text-sm font-medium transition-colors",
              current >= n
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-stone-200 bg-white text-stone-500 hover:bg-stone-50 dark:border-stone-700 dark:bg-stone-950",
            )}
          >
            {n}
          </button>
        ))}
      </div>
    );
  }

  if (type === "slider") {
    const min = field.validation?.min ?? 0;
    const max = field.validation?.max ?? 100;
    const current = Number(value ?? min);
    return (
      <div className="flex items-center gap-3">
        <input
          id={field.id}
          type="range"
          min={min}
          max={max}
          disabled={disabled}
          value={current}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full accent-teal-700"
        />
        <span className="w-10 shrink-0 text-right text-sm font-medium text-stone-600 dark:text-stone-300">
          {current}
        </span>
      </div>
    );
  }

  if (type === "gps") {
    const gps = (value as { lat?: number; lng?: number }) || {};
    return (
      <div className="grid grid-cols-2 gap-2">
        <input
          type="number"
          step="any"
          className={inputClass}
          disabled={disabled}
          placeholder="Latitude"
          value={gps.lat ?? ""}
          onChange={(e) => onChange({ ...gps, lat: e.target.value === "" ? undefined : Number(e.target.value) })}
        />
        <input
          type="number"
          step="any"
          className={inputClass}
          disabled={disabled}
          placeholder="Longitude"
          value={gps.lng ?? ""}
          onChange={(e) => onChange({ ...gps, lng: e.target.value === "" ? undefined : Number(e.target.value) })}
        />
      </div>
    );
  }

  if (type === "image" || type === "video" || type === "file" || type === "signature" || type === "audio") {
    const uri = typeof value === "object" && value ? (value as { uri?: string }).uri ?? "" : (value as string) ?? "";
    return (
      <div className="space-y-2">
        <input
          id={field.id}
          type="file"
          className={inputClass}
          disabled={disabled}
          accept={
            type === "image" || type === "signature"
              ? "image/*"
              : type === "video"
                ? "video/*"
                : type === "audio"
                  ? "audio/*"
                  : undefined
          }
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              const { api } = await import("@/lib/api");
              const uploaded = await api.uploadMediaBinary({
                file,
                fileName: file.name,
                entityType: "survey_response",
              });
              onChange({
                uri: uploaded.remote_url ?? "",
                media_id: uploaded.id,
                file_name: uploaded.file_name,
                mime_type: uploaded.mime_type,
              });
            } catch (err) {
              console.error(err);
              onChange({ uri: "", error: err instanceof Error ? err.message : "Upload failed" });
            }
          }}
        />
        {uri ? (
          <p className="truncate text-xs text-stone-500">
            Uploaded:{" "}
            <a href={uri} className="text-teal-700 underline" target="_blank" rel="noreferrer">
              {uri}
            </a>
          </p>
        ) : null}
      </div>
    );
  }

  if (type === "qr_code" || type === "barcode") {
    return (
      <input
        id={field.id}
        type="text"
        className={inputClass}
        disabled={disabled}
        placeholder={type === "qr_code" ? "Scanned QR value" : "Scanned barcode value"}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  if (type === "matrix" || type === "repeat_group") {
    const text = value ? JSON.stringify(value) : "";
    return (
      <textarea
        id={field.id}
        className={textareaClass}
        disabled={disabled}
        placeholder="JSON value"
        value={text}
        onChange={(e) => {
          try {
            onChange(e.target.value ? JSON.parse(e.target.value) : undefined);
          } catch {
            /* keep raw text buffered until valid JSON — ignore parse errors while typing */
          }
        }}
      />
    );
  }

  // Fallback: text
  return (
    <input
      id={field.id}
      type="text"
      className={inputClass}
      disabled={disabled}
      required={field.required}
      placeholder={field.placeholder}
      value={(value as string) ?? ""}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function SurveyFormRenderer({ page, answers, onChange, readOnly, errors }: Props) {
  return (
    <div className="space-y-6">
      {(page.sections || []).map((section) => (
        <div key={section.id} className="space-y-4">
          {section.title && (
            <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
              {section.title}
            </h3>
          )}
          <div className="space-y-4">
            {(section.fields || []).map((field) => {
              if (field.hidden) return null;
              if (!evaluateShowIf(answers, field)) return null;

              if (field.type === "section_header") {
                return (
                  <div key={field.id} className="border-t border-stone-200 pt-3 dark:border-stone-800">
                    <p className="font-display text-base font-semibold text-stone-800 dark:text-stone-100">
                      {field.label}
                    </p>
                    {field.help_text && (
                      <p className="mt-1 text-sm text-stone-500">{field.help_text}</p>
                    )}
                  </div>
                );
              }

              return (
                <div key={field.id}>
                  <Label htmlFor={field.id}>
                    {field.label}
                    {field.required ? " *" : ""}
                  </Label>
                  <div className="mt-1">
                    <FieldWidget
                      field={field}
                      value={answers[field.id]}
                      onChange={(value) => onChange(field.id, value)}
                      readOnly={readOnly}
                    />
                  </div>
                  {field.help_text && (
                    <p className="mt-1 text-xs text-stone-500">{field.help_text}</p>
                  )}
                  {errors?.[field.id] && (
                    <p className="mt-1 text-xs text-rose-600">{errors[field.id]}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
