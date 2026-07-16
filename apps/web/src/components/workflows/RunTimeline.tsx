"use client";

import type { WorkflowRunDetail } from "@/lib/api";
import { StatusBadge } from "@/components/ui/status-badge";

function fmt(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function RunTimeline({ run }: { run: WorkflowRunDetail }) {
  const steps = [...(run.steps ?? [])].sort((a, b) => a.step_index - b.step_index);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-stone-100 p-3 dark:border-stone-900">
          <p className="text-xs text-stone-400">Status</p>
          <div className="mt-1">
            <StatusBadge status={run.status} />
          </div>
        </div>
        <div className="rounded-xl border border-stone-100 p-3 dark:border-stone-900">
          <p className="text-xs text-stone-400">Trigger</p>
          <p className="mt-1 text-sm text-stone-700 dark:text-stone-200">
            {run.trigger_type}
            {run.trigger_event ? ` · ${run.trigger_event}` : ""}
          </p>
        </div>
        <div className="rounded-xl border border-stone-100 p-3 dark:border-stone-900">
          <p className="text-xs text-stone-400">Started</p>
          <p className="mt-1 text-sm text-stone-700 dark:text-stone-200">
            {fmt(run.started_at)}
          </p>
        </div>
        <div className="rounded-xl border border-stone-100 p-3 dark:border-stone-900">
          <p className="text-xs text-stone-400">Finished</p>
          <p className="mt-1 text-sm text-stone-700 dark:text-stone-200">
            {fmt(run.finished_at)}
          </p>
        </div>
      </div>

      {run.error_message && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
          {run.error_message}
        </p>
      )}

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-400">
          Steps
        </p>
        {steps.length === 0 && (
          <p className="text-sm text-stone-400">No steps recorded for this run.</p>
        )}
        <ol className="space-y-2">
          {steps.map((step) => (
            <li
              key={step.id}
              className="flex items-start gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-xs font-semibold text-stone-500 dark:bg-stone-800 dark:text-stone-400">
                {step.step_index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-stone-800 dark:text-stone-100">
                    {step.action_type}
                  </span>
                  <StatusBadge status={step.status} />
                </div>
                <p className="text-xs text-stone-400">
                  {step.action_id}
                  {step.attempt_count > 1 ? ` · ${step.attempt_count} attempts` : ""}
                  {step.finished_at ? ` · ${fmt(step.finished_at)}` : ""}
                </p>
                {step.error_message && (
                  <p className="mt-1 text-xs text-rose-600">{step.error_message}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
