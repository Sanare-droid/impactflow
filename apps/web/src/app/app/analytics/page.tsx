"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

function MetricGrid({
  title,
  description,
  entries,
}: {
  title: string;
  description: string;
  entries: [string, unknown][];
}) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className="rounded-xl border border-stone-100 px-3 py-3 dark:border-stone-800"
          >
            <dt className="text-xs uppercase tracking-wide text-stone-500">
              {key.replaceAll("_", " ")}
            </dt>
            <dd className="mt-1 font-display text-2xl font-semibold">
              {typeof value === "number" || typeof value === "string" ? String(value) : "—"}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: () => api.analyticsOverview(),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Analytics</h1>
        <p className="mt-2 text-stone-500">
          Cross-module overview for delivery, finance, MEAL, and field operations.
        </p>
      </div>

      {error && (
        <Card className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
          {(error as Error).message}
        </Card>
      )}

      {isLoading && <p className="text-sm text-stone-400">Loading analytics…</p>}

      {data && (
        <div className="grid gap-6 xl:grid-cols-2">
          <MetricGrid
            title="Delivery"
            description="Programs, projects, and tasks."
            entries={Object.entries(data.delivery)}
          />
          <MetricGrid
            title="Finance"
            description="Donors, grants, and spend."
            entries={Object.entries(data.finance)}
          />
          <MetricGrid
            title="MEAL"
            description="Frameworks, indicators, and evaluations."
            entries={Object.entries(data.meal)}
          />
          <MetricGrid
            title="Field"
            description="Communities, households, beneficiaries."
            entries={Object.entries(data.field)}
          />
          <MetricGrid
            title="Insights"
            description="Reports, dashboards, maps, evidence."
            entries={Object.entries(data.insights)}
          />
          <Card>
            <CardTitle>Distributions</CardTitle>
            <CardDescription>Report status and evidence types.</CardDescription>
            <div className="mt-5 grid gap-6 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium">Reports by status</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {Object.entries(data.reports_by_status).length === 0 && (
                    <li className="text-stone-400">No reports yet.</li>
                  )}
                  {Object.entries(data.reports_by_status).map(([k, v]) => (
                    <li key={k} className="flex justify-between gap-4">
                      <span className="capitalize text-stone-500">{k.replaceAll("_", " ")}</span>
                      <span className="font-medium">{v}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium">Evidence by type</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {Object.entries(data.evidence_by_type).length === 0 && (
                    <li className="text-stone-400">No evidence yet.</li>
                  )}
                  {Object.entries(data.evidence_by_type).map(([k, v]) => (
                    <li key={k} className="flex justify-between gap-4">
                      <span className="capitalize text-stone-500">{k.replaceAll("_", " ")}</span>
                      <span className="font-medium">{v}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
