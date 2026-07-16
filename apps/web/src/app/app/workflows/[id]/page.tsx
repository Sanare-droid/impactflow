"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, type TabItem } from "@/components/ui/tabs";
import { WorkflowBuilder } from "@/components/workflows/WorkflowBuilder";
import { WorkflowRuns } from "@/components/workflows/WorkflowRuns";
import { WorkflowSchedules } from "@/components/workflows/WorkflowSchedules";
import { WorkflowApprovals } from "@/components/workflows/WorkflowApprovals";

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();
  const workflowId = params.id;
  const qc = useQueryClient();
  const [tab, setTab] = useState("builder");
  const [banner, setBanner] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: workflow, isLoading } = useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => api.getWorkflow(workflowId),
  });

  const approvalsQuery = useQuery({
    queryKey: ["workflow-approvals"],
    queryFn: () => api.listWorkflowApprovals({ status: "pending" }),
  });
  const pendingApprovals = approvalsQuery.data?.meta.total ?? 0;

  const run = useMutation({
    mutationFn: () => api.runWorkflow(workflowId),
    onSuccess: async () => {
      setBanner("Manual run queued.");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["workflow-runs", workflowId] });
      setTab("runs");
    },
    onError: (err: Error) => setError(err.message),
  });

  const activate = useMutation({
    mutationFn: () => api.activateWorkflow(workflowId),
    onSuccess: async () => {
      setBanner("Workflow activated.");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["workflow", workflowId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading || !workflow) {
    return <p className="text-sm text-stone-400">Loading workflow…</p>;
  }

  const tabs: TabItem[] = [
    { id: "builder", label: "Builder" },
    { id: "runs", label: "Runs" },
    { id: "schedules", label: "Schedules" },
    ...(pendingApprovals > 0
      ? [{ id: "approvals", label: `Approvals (${pendingApprovals})` }]
      : []),
  ];

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <Link
          href="/app/workflows"
          className="text-sm text-teal-700 dark:text-teal-300"
        >
          ← Workflows
        </Link>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-display text-3xl font-semibold tracking-tight">
              {workflow.name}
            </h1>
            <StatusBadge status={workflow.status} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={run.isPending || workflow.status === "archived"}
              onClick={() => run.mutate()}
            >
              <Play className="h-3.5 w-3.5" />{" "}
              {run.isPending ? "Running…" : "Manual run"}
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={activate.isPending || workflow.status === "archived"}
              onClick={() => activate.mutate()}
            >
              <Zap className="h-3.5 w-3.5" />{" "}
              {activate.isPending ? "Activating…" : "Activate"}
            </Button>
          </div>
        </div>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-stone-500">
          <span>{workflow.code}</span>
          <span>· v{workflow.current_version}</span>
          {workflow.category && <span>· {workflow.category}</span>}
        </p>
        {workflow.description && (
          <p className="mt-1 max-w-2xl text-sm text-stone-500">
            {workflow.description}
          </p>
        )}
        {banner && (
          <p className="mt-3 text-sm text-teal-700 dark:text-teal-300">{banner}</p>
        )}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </div>

      <Tabs items={tabs} active={tab} onChange={setTab} />

      {tab === "builder" && <WorkflowBuilder workflow={workflow} />}
      {tab === "runs" && <WorkflowRuns workflow={workflow} />}
      {tab === "schedules" && <WorkflowSchedules workflow={workflow} />}
      {tab === "approvals" && <WorkflowApprovals />}
    </div>
  );
}
