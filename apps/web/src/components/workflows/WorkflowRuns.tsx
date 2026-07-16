"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, X } from "lucide-react";
import { api, type Workflow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { RunTimeline } from "./RunTimeline";

function fmt(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function WorkflowRuns({ workflow }: { workflow: Workflow }) {
  const qc = useQueryClient();
  const [openId, setOpenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runsQuery = useQuery({
    queryKey: ["workflow-runs", workflow.id],
    queryFn: () => api.listWorkflowRuns({ workflow_id: workflow.id }),
    refetchInterval: 15_000,
  });

  const detailQuery = useQuery({
    queryKey: ["workflow-run", openId],
    queryFn: () => api.getWorkflowRun(openId as string),
    enabled: Boolean(openId),
  });

  const cancel = useMutation({
    mutationFn: (id: string) => api.cancelWorkflowRun(id),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["workflow-runs", workflow.id] });
      if (openId) await qc.invalidateQueries({ queryKey: ["workflow-run", openId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const runs = runsQuery.data?.items ?? [];
  const activeStatuses = new Set(["pending", "queued", "running", "waiting"]);

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Runs</CardTitle>
            <CardDescription>Recent executions of this workflow.</CardDescription>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => runsQuery.refetch()}
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
        <div className="mt-4 space-y-2">
          {runsQuery.isLoading && (
            <p className="text-sm text-stone-400">Loading runs…</p>
          )}
          {!runsQuery.isLoading && runs.length === 0 && (
            <EmptyState
              title="No runs yet"
              description="Trigger a manual run or activate the workflow to see executions here."
            />
          )}
          {runs.map((run) => (
            <div
              key={run.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <StatusBadge status={run.status} />
                  <span className="text-sm text-stone-600 dark:text-stone-300">
                    {run.trigger_type}
                  </span>
                </div>
                <p className="mt-1 text-xs text-stone-400">
                  {fmt(run.started_at || run.created_at)}
                  {run.attempt_count > 1 ? ` · ${run.attempt_count} attempts` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setOpenId(run.id)}
                >
                  View
                </Button>
                {activeStatuses.has(run.status) && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={cancel.isPending}
                    onClick={() => cancel.mutate(run.id)}
                  >
                    <X className="h-3.5 w-3.5" /> Cancel
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {openId && (
        <Card>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">Run detail</CardTitle>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              onClick={() => setOpenId(null)}
              aria-label="Close run detail"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-4">
            {detailQuery.isLoading || !detailQuery.data ? (
              <p className="text-sm text-stone-400">Loading run…</p>
            ) : (
              <RunTimeline run={detailQuery.data} />
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
