"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { api, type Survey } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

export function SurveyResponses({ survey }: { survey: Survey }) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["survey-responses", survey.id],
    queryFn: () => api.listSurveyResponses({ survey_id: survey.id, page_size: 100 }),
  });

  const download = async (format: "csv" | "html" | "xlsx", filename: string, mime: string) => {
    setExporting(format);
    setError(null);
    try {
      const body = await api.exportSurveyResponses(survey.id, format);
      const blob = new Blob([body], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(null);
    }
  };

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle>Responses</CardTitle>
          <CardDescription>All submitted and draft responses for this survey.</CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!!exporting}
            onClick={() => download("csv", `${survey.code}-responses.csv`, "text/csv")}
          >
            <Download className="h-3.5 w-3.5" /> {exporting === "csv" ? "…" : "CSV"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!!exporting}
            onClick={() =>
              download("xlsx", `${survey.code}-responses.xls`, "application/vnd.ms-excel")
            }
          >
            <Download className="h-3.5 w-3.5" /> {exporting === "xlsx" ? "…" : "Excel"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!!exporting}
            onClick={() => download("html", `${survey.code}-responses.html`, "text/html")}
          >
            <Download className="h-3.5 w-3.5" /> {exporting === "html" ? "…" : "PDF (HTML)"}
          </Button>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

      <div className="mt-4 overflow-x-auto">
        {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
        {!isLoading && (data?.items.length ?? 0) === 0 && (
          <EmptyState title="No responses yet" description="Responses submitted via Capture will appear here." />
        )}
        {(data?.items.length ?? 0) > 0 && (
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Respondent</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Version</th>
                <th className="pb-3 font-medium">Submitted</th>
                <th className="pb-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((r) => (
                <tr key={r.id} className="border-b border-stone-100 last:border-0 dark:border-stone-900">
                  <td className="py-3 font-medium">{r.respondent_name || "Anonymous"}</td>
                  <td className="py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="py-3 text-stone-500">v{r.version}</td>
                  <td className="py-3 text-stone-500">
                    {r.submitted_at ? new Date(r.submitted_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-3 text-stone-500">{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
