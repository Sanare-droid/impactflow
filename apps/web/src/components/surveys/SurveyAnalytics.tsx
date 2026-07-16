"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type Survey } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

export function SurveyAnalytics({ survey }: { survey: Survey }) {
  const { data, isLoading } = useQuery({
    queryKey: ["survey-analytics", survey.id],
    queryFn: () => api.getSurveyAnalytics(survey.id),
  });

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-stone-400">Loading analytics…</p>
      </Card>
    );
  }

  if (!data || data.total_responses === 0) {
    return (
      <Card>
        <CardTitle>Analytics</CardTitle>
        <CardDescription>Response counts and field-level histograms.</CardDescription>
        <div className="mt-4">
          <EmptyState title="No data yet" description="Analytics populate once responses start coming in." />
        </div>
      </Card>
    );
  }

  const histograms = Object.entries(data.field_histograms || {});

  return (
    <div className="space-y-4">
      <Card>
        <CardTitle>Overview</CardTitle>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-stone-100 p-4 dark:border-stone-900">
            <p className="text-2xl font-semibold text-stone-900 dark:text-stone-50">{data.total_responses}</p>
            <p className="text-xs text-stone-500">Total responses</p>
          </div>
          {Object.entries(data.status_counts || {}).map(([status, count]) => (
            <div key={status} className="rounded-xl border border-stone-100 p-4 dark:border-stone-900">
              <p className="text-2xl font-semibold text-stone-900 dark:text-stone-50">{count}</p>
              <p className="text-xs capitalize text-stone-500">{status.replaceAll("_", " ")}</p>
            </div>
          ))}
        </div>
      </Card>

      {histograms.length > 0 && (
        <Card>
          <CardTitle>Field breakdown</CardTitle>
          <CardDescription>Distribution of answers for choice-type fields.</CardDescription>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {histograms.map(([fieldId, hist]) => {
              const counts = Object.entries(hist.counts || {});
              const max = Math.max(1, ...counts.map(([, c]) => c));
              return (
                <div key={fieldId} className="rounded-xl border border-stone-100 p-4 dark:border-stone-900">
                  <p className="text-sm font-medium text-stone-800 dark:text-stone-100">{hist.label}</p>
                  <div className="mt-3 space-y-2">
                    {counts.length === 0 && <p className="text-xs text-stone-400">No answers yet.</p>}
                    {counts.map(([value, count]) => (
                      <div key={value} className="flex items-center gap-2 text-xs">
                        <span className="w-20 shrink-0 truncate text-stone-500">{value || "(blank)"}</span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100 dark:bg-stone-800">
                          <div
                            className="h-full rounded-full bg-teal-600"
                            style={{ width: `${(count / max) * 100}%` }}
                          />
                        </div>
                        <span className="w-6 shrink-0 text-right font-medium text-stone-600 dark:text-stone-300">
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
