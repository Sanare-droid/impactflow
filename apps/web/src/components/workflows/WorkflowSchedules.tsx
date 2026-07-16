"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api, type Workflow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

const selectClass =
  "flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100";

const CADENCES = [
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "cron", label: "Custom (cron)" },
];

function fmt(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function WorkflowSchedules({ workflow }: { workflow: Workflow }) {
  const qc = useQueryClient();
  const [cadence, setCadence] = useState("daily");
  const [cronExpr, setCronExpr] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [error, setError] = useState<string | null>(null);

  const schedulesQuery = useQuery({
    queryKey: ["workflow-schedules", workflow.id],
    queryFn: () => api.listWorkflowSchedules(workflow.id),
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["workflow-schedules", workflow.id] });

  const create = useMutation({
    mutationFn: () =>
      api.createWorkflowSchedule(workflow.id, {
        cadence,
        cron_expr: cadence === "cron" ? cronExpr || undefined : undefined,
        timezone: timezone || "UTC",
        enabled: true,
      }),
    onSuccess: async () => {
      setCronExpr("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const toggle = useMutation({
    mutationFn: (input: { id: string; enabled: boolean }) =>
      api.updateWorkflowSchedule(workflow.id, input.id, { enabled: input.enabled }),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteWorkflowSchedule(workflow.id, id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const schedules = schedulesQuery.data ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardTitle>Add schedule</CardTitle>
        <CardDescription>
          Run this workflow automatically on a cadence.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="cadence">Cadence</Label>
            <select
              id="cadence"
              className={selectClass}
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
            >
              {CADENCES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="timezone">Timezone</Label>
            <Input
              id="timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="UTC"
            />
          </div>
          {cadence === "cron" && (
            <div>
              <Label htmlFor="cron">Cron expression</Label>
              <Input
                id="cron"
                value={cronExpr}
                onChange={(e) => setCronExpr(e.target.value)}
                placeholder="0 9 * * 1"
              />
            </div>
          )}
          {error && <p className="text-sm text-rose-600 md:col-span-3">{error}</p>}
          <div className="md:col-span-3">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Adding…" : "Add schedule"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Schedules</CardTitle>
        <div className="mt-4 space-y-2">
          {schedulesQuery.isLoading && (
            <p className="text-sm text-stone-400">Loading schedules…</p>
          )}
          {!schedulesQuery.isLoading && schedules.length === 0 && (
            <EmptyState
              title="No schedules"
              description="Add a cadence to run this workflow automatically."
            />
          )}
          {schedules.map((s) => (
            <div
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium capitalize text-stone-800 dark:text-stone-100">
                    {s.cadence}
                    {s.cron_expr ? ` · ${s.cron_expr}` : ""}
                  </span>
                  <StatusBadge status={s.enabled ? "active" : "inactive"} />
                </div>
                <p className="mt-1 text-xs text-stone-400">
                  {s.timezone} · next {fmt(s.next_run_at)} · last {fmt(s.last_run_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={toggle.isPending}
                  onClick={() => toggle.mutate({ id: s.id, enabled: !s.enabled })}
                >
                  {s.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(s.id)}
                  title="Delete schedule"
                >
                  <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
