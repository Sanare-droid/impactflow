"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

function fmt(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function WorkflowApprovals() {
  const qc = useQueryClient();
  const [comments, setComments] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const approvalsQuery = useQuery({
    queryKey: ["workflow-approvals"],
    queryFn: () => api.listWorkflowApprovals({ status: "pending" }),
    refetchInterval: 20_000,
  });

  const decide = useMutation({
    mutationFn: (input: {
      id: string;
      decision: "approved" | "rejected" | "returned";
    }) => api.decideWorkflowApproval(input.id, input.decision, comments[input.id]),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["workflow-approvals"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const approvals = approvalsQuery.data?.items ?? [];

  return (
    <Card>
      <CardTitle>Pending approvals</CardTitle>
      <CardDescription>
        Approval steps waiting on a decision across your workflows.
      </CardDescription>
      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      <div className="mt-4 space-y-3">
        {approvalsQuery.isLoading && (
          <p className="text-sm text-stone-400">Loading approvals…</p>
        )}
        {!approvalsQuery.isLoading && approvals.length === 0 && (
          <EmptyState
            title="No pending approvals"
            description="Approval requests raised by workflow runs appear here."
          />
        )}
        {approvals.map((a) => (
          <div
            key={a.id}
            className="space-y-2 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-stone-800 dark:text-stone-100">
                Run {a.run_id.slice(0, 8)}
              </span>
              <StatusBadge status={a.status} />
            </div>
            <p className="text-xs text-stone-400">
              Requested {fmt(a.created_at)}
              {a.due_at ? ` · due ${fmt(a.due_at)}` : ""}
            </p>
            <input
              className="flex h-9 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100"
              placeholder="Optional comment"
              value={comments[a.id] ?? ""}
              onChange={(e) =>
                setComments((prev) => ({ ...prev, [a.id]: e.target.value }))
              }
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: a.id, decision: "approved" })}
              >
                Approve
              </Button>
              <Button
                type="button"
                size="sm"
                variant="danger"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: a.id, decision: "rejected" })}
              >
                Reject
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: a.id, decision: "returned" })}
              >
                Return
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
