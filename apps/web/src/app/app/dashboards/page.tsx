"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const METRIC_OPTIONS = [
  "programs_count",
  "projects_count",
  "active_indicators_count",
  "active_beneficiaries_count",
  "open_tasks_count",
  "surveys_count",
] as const;

export default function DashboardsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [widgetMetric, setWidgetMetric] = useState<string>(METRIC_OPTIONS[0]);

  const { data, isLoading } = useQuery({
    queryKey: ["saved-dashboards"],
    queryFn: () => api.listSavedDashboards(),
  });
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.dashboardStats(),
  });

  const selected = useMemo(
    () => data?.items.find((d) => d.id === selectedId) ?? data?.items[0] ?? null,
    [data, selectedId],
  );

  const create = useMutation({
    mutationFn: () =>
      api.createSavedDashboard({
        name,
        description: description || undefined,
        status: "active",
        widgets: [
          { id: "programs", type: "metric", metric: "programs_count" },
          { id: "indicators", type: "metric", metric: "active_indicators_count" },
          { id: "beneficiaries", type: "metric", metric: "active_beneficiaries_count" },
        ],
      }),
    onSuccess: async (created) => {
      setName("");
      setDescription("");
      setError(null);
      setSelectedId(created.id);
      await qc.invalidateQueries({ queryKey: ["saved-dashboards"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const addWidget = useMutation({
    mutationFn: async () => {
      if (!selected) throw new Error("Select a dashboard");
      const widgets = [
        ...(selected.widgets ?? []),
        {
          id: `w-${Date.now()}`,
          type: "metric",
          metric: widgetMetric,
        },
      ];
      return api.updateSavedDashboard(selected.id, { widgets });
    },
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["saved-dashboards"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  function metricValue(metric: string): string | number {
    if (!stats) return "—";
    const map = stats as Record<string, unknown>;
    const val = map[metric];
    return typeof val === "number" || typeof val === "string" ? val : "—";
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Dashboards</h1>
        <p className="mt-2 text-stone-500">
          View saved layouts and add metric widgets for program and MEAL oversight.
        </p>
      </div>

      <Card>
        <CardTitle>Create dashboard</CardTitle>
        <CardDescription>Starts with a default delivery / MEAL / field widget set.</CardDescription>
        <form
          className="mt-4 grid gap-3"
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
            <Label htmlFor="desc">Description</Label>
            <Input
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create dashboard"}
            </Button>
          </div>
        </form>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <Card>
          <CardTitle>Saved</CardTitle>
          <div className="mt-4 space-y-2">
            {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
            {data?.items.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => setSelectedId(d.id)}
                className={`block w-full rounded-xl px-3 py-2 text-left text-sm ${
                  selected?.id === d.id
                    ? "bg-teal-700 text-white"
                    : "bg-stone-50 hover:bg-stone-100 dark:bg-stone-900"
                }`}
              >
                <span className="font-medium">{d.name}</span>
                <span className="mt-0.5 block text-xs opacity-80">
                  {(d.widgets ?? []).length} widgets
                </span>
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>{selected?.name ?? "Select a dashboard"}</CardTitle>
              <CardDescription>
                {selected?.description || "Live metric widgets from workspace stats."}
              </CardDescription>
            </div>
            {selected ? <StatusBadge status={selected.status} /> : null}
          </div>

          {selected ? (
            <>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(selected.widgets ?? []).map((w) => {
                  const metric = String((w as { metric?: string }).metric ?? "programs_count");
                  return (
                    <div
                      key={String((w as { id?: string }).id ?? metric)}
                      className="rounded-2xl border border-stone-200 bg-gradient-to-br from-teal-50/80 to-white p-4 dark:border-stone-800 dark:from-stone-900 dark:to-stone-950"
                    >
                      <p className="text-xs uppercase tracking-wide text-stone-400">
                        {metric.replaceAll("_", " ")}
                      </p>
                      <p className="mt-2 font-display text-3xl font-semibold text-stone-900 dark:text-stone-50">
                        {metricValue(metric)}
                      </p>
                    </div>
                  );
                })}
              </div>
              <form
                className="mt-6 flex flex-wrap items-end gap-3"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  addWidget.mutate();
                }}
              >
                <div>
                  <Label htmlFor="metric">Add metric widget</Label>
                  <select
                    id="metric"
                    className="mt-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                    value={widgetMetric}
                    onChange={(e) => setWidgetMetric(e.target.value)}
                  >
                    {METRIC_OPTIONS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
                <Button type="submit" disabled={addWidget.isPending}>
                  {addWidget.isPending ? "Adding…" : "Add widget"}
                </Button>
              </form>
            </>
          ) : (
            <p className="mt-4 text-sm text-stone-500">Create or select a dashboard to view widgets.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
