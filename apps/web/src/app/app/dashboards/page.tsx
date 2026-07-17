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

type WidgetType = "metric" | "chart" | "table";

type DashWidget = {
  id?: string;
  type?: string;
  metric?: string;
  metrics?: string[];
  title?: string;
};

export default function DashboardsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [widgetMetric, setWidgetMetric] = useState<string>(METRIC_OPTIONS[0]);
  const [widgetType, setWidgetType] = useState<WidgetType>("metric");

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
          {
            id: "overview-chart",
            type: "chart",
            title: "Delivery overview",
            metrics: ["programs_count", "projects_count", "open_tasks_count"],
          },
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
      const id = `w-${Date.now()}`;
      let next: DashWidget;
      if (widgetType === "chart") {
        next = {
          id,
          type: "chart",
          title: "Metric chart",
          metrics: [widgetMetric, ...METRIC_OPTIONS.filter((m) => m !== widgetMetric).slice(0, 3)],
        };
      } else if (widgetType === "table") {
        next = {
          id,
          type: "table",
          title: "Metrics table",
          metrics: [...METRIC_OPTIONS],
        };
      } else {
        next = { id, type: "metric", metric: widgetMetric };
      }
      const widgets = [...(selected.widgets ?? []), next];
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

  function numericMetric(metric: string): number {
    const v = metricValue(metric);
    return typeof v === "number" ? v : 0;
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Dashboards</h1>
        <p className="mt-2 text-stone-500">
          Saved layouts with metric, chart, and table widgets for program and MEAL oversight.
        </p>
      </div>

      <Card>
        <CardTitle>Create dashboard</CardTitle>
        <CardDescription>Starts with metrics plus an overview chart.</CardDescription>
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
                {selected?.description || "Live widgets from workspace stats."}
              </CardDescription>
            </div>
            {selected ? <StatusBadge status={selected.status} /> : null}
          </div>

          {selected ? (
            <>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                {(selected.widgets ?? []).map((raw) => {
                  const w = raw as DashWidget;
                  const key = String(w.id ?? w.metric ?? Math.random());
                  if (w.type === "chart") {
                    const metrics = (w.metrics?.length ? w.metrics : [w.metric || "programs_count"]).filter(
                      Boolean,
                    ) as string[];
                    const values = metrics.map((m) => numericMetric(m));
                    const max = Math.max(...values, 1);
                    return (
                      <div
                        key={key}
                        className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-stone-950 lg:col-span-2"
                      >
                        <p className="text-xs uppercase tracking-wide text-stone-400">
                          {w.title || "Chart"}
                        </p>
                        <svg
                          viewBox="0 0 480 180"
                          className="mt-3 w-full"
                          role="img"
                          aria-label={w.title || "Chart"}
                        >
                          {metrics.map((m, i) => {
                            const barW = 480 / metrics.length - 16;
                            const x = i * (480 / metrics.length) + 8;
                            const h = (values[i] / max) * 120;
                            const y = 140 - h;
                            return (
                              <g key={m}>
                                <rect
                                  x={x}
                                  y={y}
                                  width={barW}
                                  height={h}
                                  rx={6}
                                  fill="#0F766E"
                                  opacity={0.85}
                                />
                                <text
                                  x={x + barW / 2}
                                  y={156}
                                  textAnchor="middle"
                                  className="fill-stone-500"
                                  fontSize="10"
                                >
                                  {m.replaceAll("_", " ").slice(0, 14)}
                                </text>
                                <text
                                  x={x + barW / 2}
                                  y={y - 6}
                                  textAnchor="middle"
                                  className="fill-stone-700"
                                  fontSize="11"
                                >
                                  {values[i]}
                                </text>
                              </g>
                            );
                          })}
                        </svg>
                      </div>
                    );
                  }
                  if (w.type === "table") {
                    const metrics = (w.metrics?.length ? w.metrics : [...METRIC_OPTIONS]) as string[];
                    return (
                      <div
                        key={key}
                        className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-stone-950 lg:col-span-2"
                      >
                        <p className="text-xs uppercase tracking-wide text-stone-400">
                          {w.title || "Table"}
                        </p>
                        <table className="mt-3 w-full text-left text-sm">
                          <thead>
                            <tr className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
                              <th className="py-2 font-medium">Metric</th>
                              <th className="py-2 font-medium">Value</th>
                            </tr>
                          </thead>
                          <tbody>
                            {metrics.map((m) => (
                              <tr
                                key={m}
                                className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                              >
                                <td className="py-2 capitalize text-stone-600 dark:text-stone-300">
                                  {m.replaceAll("_", " ")}
                                </td>
                                <td className="py-2 font-display text-lg font-semibold">
                                  {metricValue(m)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  }
                  const metric = String(w.metric ?? "programs_count");
                  return (
                    <div
                      key={key}
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
                  <Label htmlFor="wtype">Widget type</Label>
                  <select
                    id="wtype"
                    className="mt-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                    value={widgetType}
                    onChange={(e) => setWidgetType(e.target.value as WidgetType)}
                  >
                    <option value="metric">Metric</option>
                    <option value="chart">Chart</option>
                    <option value="table">Table</option>
                  </select>
                </div>
                {widgetType !== "table" && (
                  <div>
                    <Label htmlFor="metric">Primary metric</Label>
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
                )}
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
