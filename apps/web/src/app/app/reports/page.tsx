"use client";

import { FormEvent, Fragment, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Download, FileStack } from "lucide-react";
import {
  api,
  type Report,
  type ReportExportFormat,
  type ReportVersion,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const EXPORT_FORMATS: { format: ReportExportFormat; label: string; ext: string }[] = [
  { format: "markdown", label: "MD", ext: "md" },
  { format: "html", label: "HTML", ext: "html" },
  { format: "docx", label: "DOCX", ext: "docx" },
  { format: "pptx", label: "PPTX", ext: "pptx" },
  // Backend serves SpreadsheetML — must use .xls so Excel opens content
  { format: "xlsx", label: "Excel", ext: "xls" },
  { format: "csv", label: "CSV", ext: "csv" },
];

export default function ReportsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [templateCode, setTemplateCode] = useState("");
  const [generateNarrative, setGenerateNarrative] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [versionsFor, setVersionsFor] = useState<string | null>(null);
  const [versions, setVersions] = useState<ReportVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.listReports(),
  });

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ["report-templates"],
    queryFn: () => api.listReportTemplates(),
  });

  const clone = useMutation({
    mutationFn: (code: string) =>
      api.cloneReportTemplate({ code, name: undefined }),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["report-templates"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const build = useMutation({
    mutationFn: () =>
      api.buildReport({
        name,
        template_code: templateCode || undefined,
        generate_narrative: generateNarrative,
        narrative_type: "donor",
        save_version: true,
      }),
    onSuccess: async () => {
      setName("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["reports"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      await qc.invalidateQueries({ queryKey: ["executive-dashboard"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const approve = useMutation({
    mutationFn: (id: string) => api.approveReport(id),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const publish = useMutation({
    mutationFn: (id: string) => api.publishReport(id),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["reports"] });
      await qc.invalidateQueries({ queryKey: ["executive-dashboard"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  async function openVersions(reportId: string) {
    if (versionsFor === reportId) {
      setVersionsFor(null);
      return;
    }
    setVersionsFor(reportId);
    setVersionsLoading(true);
    try {
      const res = await api.listReportVersions(reportId);
      setVersions(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load versions");
    } finally {
      setVersionsLoading(false);
    }
  }

  async function exportReport(r: Report, format: ReportExportFormat, ext: string) {
    try {
      await api.downloadReportExport(r.id, format, `${r.code}.${ext}`);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  const templateItems = templates?.items ?? [];
  const systemTemplates = templateItems.filter((t) => t.is_system !== false && !t.organization_id);
  const orgTemplates = templateItems.filter((t) => t.organization_id);

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="mt-2 text-stone-500">
          Donor templates, AI-assisted builds, approve/publish workflow, and multi-format export.
        </p>
      </div>

      {error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </p>
      )}

      <Card>
        <CardTitle className="flex items-center gap-2">
          <FileStack className="h-4 w-4 text-teal-700 dark:text-teal-400" />
          Template gallery
        </CardTitle>
        <CardDescription>
          Clone a system pack into your organization, then use it when building reports.
        </CardDescription>
        {templatesLoading && (
          <p className="mt-4 text-sm text-stone-400">Loading templates…</p>
        )}
        {!templatesLoading && templateItems.length === 0 && (
          <div className="mt-4">
            <EmptyState
              title="No templates"
              description="System donor templates will appear here once the API is available."
            />
          </div>
        )}
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[...systemTemplates, ...orgTemplates].map((t) => {
            const key = t.id ?? t.code;
            const isOrg = Boolean(t.organization_id);
            return (
              <div
                key={key}
                className="flex flex-col rounded-xl border border-stone-100 bg-stone-50/50 p-4 dark:border-stone-800 dark:bg-stone-900/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-stone-900 dark:text-stone-100">{t.name}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-stone-400">{t.code}</p>
                  </div>
                  <span className="shrink-0 rounded-md bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-stone-500 dark:bg-stone-950">
                    {isOrg ? "cloned" : t.category}
                  </span>
                </div>
                {t.description ? (
                  <p className="mt-2 line-clamp-2 text-xs text-stone-500">{t.description}</p>
                ) : null}
                <p className="mt-2 text-xs text-stone-400">
                  {(t.sections?.length ?? 0)} sections · {t.report_type}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {!isOrg && (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={clone.isPending}
                      onClick={() => clone.mutate(t.code)}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Clone
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setTemplateCode(t.code);
                      if (!name) setName(`${t.name} draft`);
                    }}
                  >
                    Use in builder
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardTitle>Build report</CardTitle>
        <CardDescription>
          Pick a template, name the package, and optionally generate an AI narrative.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            build.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Q2 Donor Progress Pack"
            />
          </div>
          <div>
            <Label htmlFor="template">Template</Label>
            <select
              id="template"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={templateCode}
              onChange={(e) => setTemplateCode(e.target.value)}
            >
              <option value="">No template (blank)</option>
              {templateItems.map((t) => (
                <option key={t.id ?? t.code} value={t.code}>
                  {t.name} ({t.code})
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="flex items-center gap-2 text-sm text-stone-700 dark:text-stone-300">
              <input
                type="checkbox"
                className="rounded border-stone-300 text-teal-700 focus:ring-teal-600"
                checked={generateNarrative}
                onChange={(e) => setGenerateNarrative(e.target.checked)}
              />
              Generate AI narrative from live portfolio data
            </label>
          </div>
          <div className="md:col-span-2">
            <Button type="submit" disabled={build.isPending || !name.trim()}>
              {build.isPending ? "Building…" : "Build report"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Report library</CardTitle>
        <CardDescription>
          Approve, publish, export, and inspect version history.
        </CardDescription>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[920px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Actions</th>
                <th className="pb-3 font-medium">Export</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={6}>
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (reports?.items.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={6} className="py-6">
                    <EmptyState
                      title="No reports yet"
                      description="Build from a template or generate an executive brief."
                      actionLabel="Executive dashboard"
                      actionHref="/app/executive"
                    />
                  </td>
                </tr>
              )}
              {reports?.items.map((r) => (
                <Fragment key={r.id}>
                  <tr className="border-b border-stone-100 last:border-0 dark:border-stone-900">
                    <td className="py-3 font-medium">{r.name}</td>
                    <td className="py-3 font-mono text-xs">{r.code}</td>
                    <td className="py-3 capitalize">{r.report_type.replaceAll("_", " ")}</td>
                    <td className="py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {(r.status === "draft" || r.status === "in_review") && (
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={approve.isPending}
                            onClick={() => approve.mutate(r.id)}
                          >
                            <Check className="h-3.5 w-3.5" />
                            Approve
                          </Button>
                        )}
                        {r.status !== "published" && (
                          <Button
                            size="sm"
                            disabled={publish.isPending}
                            onClick={() => publish.mutate(r.id)}
                          >
                            Publish
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openVersions(r.id)}
                        >
                          Versions
                        </Button>
                      </div>
                    </td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1">
                        {EXPORT_FORMATS.map((f) => (
                          <Button
                            key={f.format}
                            size="sm"
                            variant="ghost"
                            title={`Download ${f.label}`}
                            onClick={() => exportReport(r, f.format, f.ext)}
                          >
                            <Download className="h-3 w-3" />
                            {f.label}
                          </Button>
                        ))}
                      </div>
                    </td>
                  </tr>
                  {versionsFor === r.id && (
                    <tr className="bg-stone-50/80 dark:bg-stone-900/30">
                      <td colSpan={6} className="px-3 py-3">
                        {versionsLoading && (
                          <p className="text-xs text-stone-400">Loading versions…</p>
                        )}
                        {!versionsLoading && versions.length === 0 && (
                          <p className="text-xs text-stone-400">No versions saved yet.</p>
                        )}
                        {!versionsLoading && versions.length > 0 && (
                          <ul className="space-y-2 text-xs">
                            {versions.map((v) => (
                              <li
                                key={v.id}
                                className="flex flex-wrap items-center gap-3 rounded-lg border border-stone-200 bg-white px-3 py-2 dark:border-stone-800 dark:bg-stone-950"
                              >
                                <span className="font-semibold tabular-nums">v{v.version}</span>
                                <StatusBadge status={v.status} />
                                <span className="text-stone-500">
                                  {v.changelog || v.title}
                                </span>
                                <span className="ml-auto tabular-nums text-stone-400">
                                  {v.created_at
                                    ? new Date(v.created_at).toLocaleString()
                                    : "—"}
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
