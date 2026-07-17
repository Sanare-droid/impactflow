"use client";

import { FeatureGate } from "@/components/feature-gate";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Copy, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

export default function WorkflowsPage() {
  return (
    <FeatureGate feature="workflows" fallbackTitle="Workflows require Starter+">
      <WorkflowsInner />
    </FeatureGate>
  );
}

function WorkflowsInner() {
  const qc = useQueryClient();
  const router = useRouter();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => api.listWorkflows(),
  });

  const templatesQuery = useQuery({
    queryKey: ["workflow-templates"],
    queryFn: () => api.listWorkflowTemplates(),
    staleTime: 5 * 60 * 1000,
  });

  const metricsQuery = useQuery({
    queryKey: ["workflow-metrics"],
    queryFn: () => api.workflowMetrics(),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["workflows"] });

  const create = useMutation({
    mutationFn: () =>
      api.createWorkflow({
        name,
        category: category || undefined,
        status: "draft",
      }),
    onSuccess: async (wf) => {
      setName("");
      setCategory("");
      setError(null);
      await invalidate();
      router.push(`/app/workflows/${wf.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const clone = useMutation({
    mutationFn: (id: string) => api.cloneWorkflow(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const enable = useMutation({
    mutationFn: (id: string) => api.enableWorkflow(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const disable = useMutation({
    mutationFn: (id: string) => api.disableWorkflow(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.archiveWorkflow(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const cloneTemplate = useMutation({
    mutationFn: (code: string) => api.cloneWorkflowTemplate(code),
    onSuccess: async (wf) => {
      await invalidate();
      router.push(`/app/workflows/${wf.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const metrics = metricsQuery.data;
  const templates = (templatesQuery.data?.templates ?? []).filter(
    (t) => !t.workflow_id,
  );
  const workflows = (data?.items ?? []).filter((w) => !w.is_template);

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Workflows
        </h1>
        <p className="mt-2 text-stone-500">
          Automate reactions to events with triggers, conditions, and actions.
        </p>
      </div>

      {metrics && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Runs (7d)" value={metrics.runs_last_7d} />
          <MetricCard
            label="Success rate (7d)"
            value={`${Math.round((metrics.success_rate_7d ?? 0) * 100)}%`}
          />
          <MetricCard label="Queue depth" value={metrics.queue_depth} />
          <MetricCard label="Pending approvals" value={metrics.pending_approvals} />
        </div>
      )}

      <Card>
        <CardTitle>Create workflow</CardTitle>
        <CardDescription>
          Starts an empty draft you can build out in the editor.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="category">Category</Label>
            <Input
              id="category"
              placeholder="e.g. monitoring, finance"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-rose-600 md:col-span-3">{error}</p>}
          <div className="md:col-span-3">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create workflow"}
            </Button>
          </div>
        </form>
      </Card>

      {templates.length > 0 && (
        <Card>
          <CardTitle>Templates</CardTitle>
          <CardDescription>
            Clone a starter workflow and customize it for your organization.
          </CardDescription>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {templates.map((t) => (
              <div
                key={t.code}
                className="flex flex-col justify-between gap-3 rounded-xl border border-stone-100 p-4 dark:border-stone-900"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-teal-600" />
                    <span className="font-medium text-stone-800 dark:text-stone-100">
                      {t.name}
                    </span>
                  </div>
                  {t.description && (
                    <p className="mt-1 text-sm text-stone-500">{t.description}</p>
                  )}
                  {t.category && (
                    <p className="mt-1 text-xs text-stone-400">{t.category}</p>
                  )}
                </div>
                <div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={cloneTemplate.isPending}
                    onClick={() => cloneTemplate.mutate(t.code)}
                  >
                    <Copy className="h-3.5 w-3.5" /> Use template
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <CardTitle>All workflows</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {!isLoading && workflows.length === 0 && (
            <EmptyState
              title="No workflows yet"
              description="Create a draft workflow or clone a template to get started."
            />
          )}
          {workflows.map((w) => (
            <div
              key={w.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div className="min-w-0">
                <Link
                  href={`/app/workflows/${w.id}`}
                  className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                >
                  {w.name}
                </Link>
                <p className="text-xs text-stone-500">
                  {w.code} · v{w.current_version}
                  {w.category ? ` · ${w.category}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={w.status} />
                <Link
                  href={`/app/workflows/${w.id}`}
                  className="inline-flex h-8 items-center rounded-md border border-stone-200 px-3 text-xs font-medium transition-colors hover:bg-stone-50 dark:border-stone-700 dark:hover:bg-stone-900"
                >
                  Open
                </Link>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={clone.isPending}
                  onClick={() => clone.mutate(w.id)}
                  title="Clone workflow"
                >
                  <Copy className="h-3.5 w-3.5" /> Clone
                </Button>
                {w.status === "active" ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={disable.isPending}
                    onClick={() => disable.mutate(w.id)}
                  >
                    Disable
                  </Button>
                ) : (
                  w.status !== "archived" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={enable.isPending}
                      onClick={() => enable.mutate(w.id)}
                    >
                      Enable
                    </Button>
                  )
                )}
                {w.status !== "archived" && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={archive.isPending}
                    onClick={() => archive.mutate(w.id)}
                    title="Archive workflow"
                  >
                    <Archive className="h-3.5 w-3.5" /> Archive
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-stone-400">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold text-stone-900 dark:text-stone-50">
        {value}
      </p>
    </Card>
  );
}
