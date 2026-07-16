"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export default function OpsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ops-observability"],
    queryFn: () => api.getOpsObservability(),
    refetchInterval: 60_000,
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Operations</h1>
        <p className="mt-2 text-stone-500">
          Platform health — API, database, Redis, workers, and event bus.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{(error as Error).message}</p>}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardDescription>Organizations</CardDescription>
          <CardTitle className="mt-2 text-3xl">{isLoading ? "…" : data?.organizations}</CardTitle>
        </Card>
        <Card>
          <CardDescription>Users</CardDescription>
          <CardTitle className="mt-2 text-3xl">{isLoading ? "…" : data?.users}</CardTitle>
        </Card>
        <Card>
          <CardDescription>API</CardDescription>
          <CardTitle className="mt-2 text-3xl">{data?.api_health ?? "—"}</CardTitle>
        </Card>
      </div>

      <Card>
        <CardTitle>Components</CardTitle>
        <ul className="mt-4 space-y-2">
          {(data?.components ?? []).map((c) => (
            <li
              key={c.name}
              className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2 dark:bg-stone-900"
            >
              <span className="font-medium capitalize">{c.name.replace("_", " ")}</span>
              <StatusBadge status={c.status === "healthy" ? "active" : c.status} />
            </li>
          ))}
        </ul>
        {data?.generated_at && (
          <p className="mt-3 text-xs text-stone-400">
            Snapshot {new Date(data.generated_at).toLocaleString()}
          </p>
        )}
      </Card>
    </div>
  );
}
