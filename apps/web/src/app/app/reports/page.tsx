"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function ReportsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState("progress");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.listReports(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createReport({
        name,
        report_type: reportType,
        summary: summary || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setSummary("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["reports"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="mt-2 text-stone-500">Progress, donor, quarterly, and evaluation narratives.</p>
      </div>

      <Card>
        <CardTitle>New report</CardTitle>
        <CardDescription>Create a draft report package for review.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="type">Type</Label>
            <select
              id="type"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              <option value="progress">Progress</option>
              <option value="quarterly">Quarterly</option>
              <option value="annual">Annual</option>
              <option value="donor">Donor</option>
              <option value="evaluation">Evaluation</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="summary">Summary</Label>
            <Input id="summary" value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create report"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Report library</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Export</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={5}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{r.name}</td>
                  <td className="py-3 font-mono text-xs">{r.code}</td>
                  <td className="py-3 capitalize">{r.report_type}</td>
                  <td className="py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="py-3">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={async () => {
                        const md = await api.exportReportMarkdown(r.id);
                        const blob = new Blob([md], { type: "text/markdown" });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `${r.code}.md`;
                        a.click();
                        URL.revokeObjectURL(url);
                      }}
                    >
                      Markdown
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
