"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, EyeOff, Lock, Save, Upload } from "lucide-react";
import { api, type Survey, type SurveySchema, type SurveyVersionDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { FieldPalette } from "./FieldPalette";
import { SurveyBuilderCanvas } from "./SurveyBuilderCanvas";
import { PropertiesPanel } from "./PropertiesPanel";
import { SurveyFormRenderer } from "./SurveyFormRenderer";
import type { BuilderActions, BuilderSelection } from "./builder-types";
import { FALLBACK_FIELD_TYPES, defaultFieldForType, newId, normalizeSchemaForClient } from "./schema-utils";

export function SurveyBuilder({ survey, version }: { survey: Survey; version: SurveyVersionDetail }) {
  const qc = useQueryClient();
  const [schema, setSchema] = useState<SurveySchema>(() => normalizeSchemaForClient(version.schema));
  const [selection, setSelection] = useState<BuilderSelection>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [previewPage, setPreviewPage] = useState(0);
  const [unlocked, setUnlocked] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setSchema(normalizeSchemaForClient(version.schema));
    setSelection(null);
    setUnlocked(false);
  }, [version.id]);

  const fieldTypesQuery = useQuery({
    queryKey: ["survey-field-types"],
    queryFn: () => api.listFieldTypes(),
    staleTime: 5 * 60 * 1000,
  });
  const fieldTypes = fieldTypesQuery.data && fieldTypesQuery.data.length > 0 ? fieldTypesQuery.data : FALLBACK_FIELD_TYPES;

  const isPublished = survey.status === "published";
  const editable = !isPublished || unlocked;

  const invalidateSurvey = () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: ["survey", survey.id] }),
      qc.invalidateQueries({ queryKey: ["survey-versions", survey.id] }),
      qc.invalidateQueries({ queryKey: ["surveys"] }),
    ]);

  const saveSchema = useMutation({
    mutationFn: () => api.updateSurvey(survey.id, { schema }),
    onSuccess: async () => {
      setNotice("Schema saved as a new version.");
      setError(null);
      setUnlocked(false);
      await invalidateSurvey();
    },
    onError: (err: Error) => setError(err.message),
  });

  const publish = useMutation({
    mutationFn: () => api.updateSurvey(survey.id, { status: "published", publish: true }),
    onSuccess: async () => {
      setNotice("Survey published.");
      setError(null);
      await invalidateSurvey();
    },
    onError: (err: Error) => setError(err.message),
  });

  const importSchema = useMutation({
    mutationFn: (imported: SurveySchema) => api.importSurveySchema(survey.id, imported, "Imported schema"),
    onSuccess: async (detail) => {
      setSchema(normalizeSchemaForClient(detail.version.schema));
      setNotice("Schema imported as a new version.");
      setError(null);
      await invalidateSurvey();
    },
    onError: (err: Error) => setError(err.message),
  });

  const exportSchema = async () => {
    try {
      const payload = await api.exportSurveySchema(survey.id);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${survey.code}-schema.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  const handleImportFile = async (file: File) => {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const importedSchema: SurveySchema = parsed.schema ?? parsed;
      importSchema.mutate(importedSchema);
    } catch {
      setError("Could not parse JSON file.");
    }
  };

  const actions: BuilderActions = useMemo(
    () => ({
      select: setSelection,
      addPage: () =>
        setSchema((prev) => ({
          ...prev,
          pages: [
            ...(prev.pages || []),
            { id: newId("page"), title: `Page ${(prev.pages || []).length + 1}`, sections: [{ id: newId("sec"), title: "Questions", fields: [] }] },
          ],
        })),
      updatePage: (pageId, patch) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) => (p.id === pageId ? { ...p, ...patch } : p)),
        })),
      deletePage: (pageId) =>
        setSchema((prev) => ({ ...prev, pages: (prev.pages || []).filter((p) => p.id !== pageId) })),
      movePage: (pageId, dir) =>
        setSchema((prev) => {
          const pages = [...(prev.pages || [])];
          const idx = pages.findIndex((p) => p.id === pageId);
          const next = idx + dir;
          if (idx < 0 || next < 0 || next >= pages.length) return prev;
          [pages[idx], pages[next]] = [pages[next], pages[idx]];
          return { ...prev, pages };
        }),
      addSection: (pageId) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id === pageId
              ? { ...p, sections: [...p.sections, { id: newId("sec"), title: "New section", fields: [] }] }
              : p,
          ),
        })),
      updateSection: (pageId, sectionId, patch) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id !== pageId
              ? p
              : { ...p, sections: p.sections.map((s) => (s.id === sectionId ? { ...s, ...patch } : s)) },
          ),
        })),
      deleteSection: (pageId, sectionId) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id !== pageId ? p : { ...p, sections: p.sections.filter((s) => s.id !== sectionId) },
          ),
        })),
      moveSection: (pageId, sectionId, dir) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) => {
            if (p.id !== pageId) return p;
            const sections = [...p.sections];
            const idx = sections.findIndex((s) => s.id === sectionId);
            const next = idx + dir;
            if (idx < 0 || next < 0 || next >= sections.length) return p;
            [sections[idx], sections[next]] = [sections[next], sections[idx]];
            return { ...p, sections };
          }),
        })),
      addField: (pageId, sectionId, type) => {
        const field = defaultFieldForType(type);
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id !== pageId
              ? p
              : {
                  ...p,
                  sections: p.sections.map((s) =>
                    s.id !== sectionId ? s : { ...s, fields: [...s.fields, field] },
                  ),
                },
          ),
        }));
        setSelection({ kind: "field", pageId, sectionId, fieldId: field.id });
      },
      updateField: (pageId, sectionId, fieldId, patch) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id !== pageId
              ? p
              : {
                  ...p,
                  sections: p.sections.map((s) =>
                    s.id !== sectionId
                      ? s
                      : { ...s, fields: s.fields.map((f) => (f.id === fieldId ? { ...f, ...patch } : f)) },
                  ),
                },
          ),
        })),
      deleteField: (pageId, sectionId, fieldId) => {
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) =>
            p.id !== pageId
              ? p
              : {
                  ...p,
                  sections: p.sections.map((s) =>
                    s.id !== sectionId ? s : { ...s, fields: s.fields.filter((f) => f.id !== fieldId) },
                  ),
                },
          ),
        }));
        setSelection((sel) => (sel?.kind === "field" && sel.fieldId === fieldId ? null : sel));
      },
      moveField: (pageId, sectionId, fieldId, dir) =>
        setSchema((prev) => ({
          ...prev,
          pages: (prev.pages || []).map((p) => {
            if (p.id !== pageId) return p;
            return {
              ...p,
              sections: p.sections.map((s) => {
                if (s.id !== sectionId) return s;
                const fields = [...s.fields];
                const idx = fields.findIndex((f) => f.id === fieldId);
                const next = idx + dir;
                if (idx < 0 || next < 0 || next >= fields.length) return s;
                [fields[idx], fields[next]] = [fields[next], fields[idx]];
                return { ...s, fields };
              }),
            };
          }),
        })),
    }),
    [],
  );

  const disabledCanvas = !editable;
  const activeSectionForAdd = useMemo(() => {
    if (selection?.kind === "field" || selection?.kind === "section") {
      return { pageId: selection.pageId, sectionId: selection.sectionId };
    }
    const firstPage = schema.pages?.[0];
    const firstSection = firstPage?.sections?.[0];
    if (firstPage && firstSection) return { pageId: firstPage.id, sectionId: firstSection.id };
    return null;
  }, [selection, schema]);

  const previewPages = schema.pages || [];

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Builder</CardTitle>
            <CardDescription>
              {isPublished
                ? unlocked
                  ? "Editing will save as a new version when you publish or save again."
                  : "Published — start a new version to make changes."
                : "Draft schema — save to create the next version."}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => setPreviewMode((v) => !v)}>
              {previewMode ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              {previewMode ? "Exit preview" : "Preview"}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={exportSchema}>
              <Download className="h-3.5 w-3.5" /> Export JSON
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={importSchema.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-3.5 w-3.5" /> Import JSON
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImportFile(file);
                e.target.value = "";
              }}
            />
            {isPublished && !unlocked && (
              <Button type="button" size="sm" variant="secondary" onClick={() => setUnlocked(true)}>
                <Lock className="h-3.5 w-3.5" /> Start new version
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              disabled={!editable || saveSchema.isPending}
              onClick={() => saveSchema.mutate()}
            >
              <Save className="h-3.5 w-3.5" /> {saveSchema.isPending ? "Saving…" : "Save schema"}
            </Button>
            {!isPublished && (
              <Button type="button" size="sm" variant="secondary" disabled={publish.isPending} onClick={() => publish.mutate()}>
                {publish.isPending ? "Publishing…" : "Publish"}
              </Button>
            )}
          </div>
        </div>
        {notice && <p className="mt-3 text-sm text-teal-700 dark:text-teal-300">{notice}</p>}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Card>

      {previewMode ? (
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <CardTitle>Preview</CardTitle>
            {previewPages.length > 1 && (
              <div className="flex items-center gap-2 text-sm">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={previewPage === 0}
                  onClick={() => setPreviewPage((p) => Math.max(0, p - 1))}
                >
                  Prev
                </Button>
                <span className="text-stone-500">
                  Page {previewPage + 1} / {previewPages.length}
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={previewPage === previewPages.length - 1}
                  onClick={() => setPreviewPage((p) => Math.min(previewPages.length - 1, p + 1))}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
          {previewPages[previewPage] && (
            <SurveyFormRenderer page={previewPages[previewPage]} answers={{}} onChange={() => undefined} readOnly />
          )}
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[220px_1fr_300px]">
          <Card className="h-fit">
            <CardTitle className="text-sm">Field palette</CardTitle>
            <CardDescription className="mb-3">
              {activeSectionForAdd ? "Adds to the selected section." : "Add a section first."}
            </CardDescription>
            <FieldPalette
              fieldTypes={fieldTypes}
              disabled={disabledCanvas || !activeSectionForAdd}
              onAdd={(type) => {
                if (!activeSectionForAdd) return;
                actions.addField(activeSectionForAdd.pageId, activeSectionForAdd.sectionId, type);
              }}
            />
          </Card>

          <Card>
            <CardTitle className="text-sm">Canvas</CardTitle>
            <CardDescription className="mb-3">Pages → sections → fields.</CardDescription>
            <SurveyBuilderCanvas schema={schema} selection={selection} actions={actions} disabled={disabledCanvas} />
          </Card>

          <Card className="h-fit">
            <CardTitle className="text-sm">Properties</CardTitle>
            <div className="mt-3">
              <PropertiesPanel
                schema={schema}
                selection={selection}
                actions={actions}
                fieldTypes={fieldTypes}
                disabled={disabledCanvas}
              />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
