"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

export default function TasksPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["tasks", "all"],
    queryFn: () => api.listTasks(),
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers({ page_size: 100 }),
  });

  const memberLabel = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of users?.items ?? []) {
      if (!m.user) continue;
      map.set(
        m.user_id,
        `${m.user.first_name} ${m.user.last_name}`.trim() || m.user.email,
      );
    }
    return map;
  }, [users]);

  const complete = useMutation({
    mutationFn: (id: string) => api.updateTask(id, { status: "done" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const assign = useMutation({
    mutationFn: ({ id, assignee_id }: { id: string; assignee_id: string }) =>
      api.updateTask(id, { assignee_id: assignee_id || null }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Tasks</h1>
        <p className="mt-2 text-stone-500">
          Cross-project action items. Assign teammates so work appears in their field app.
        </p>
      </div>

      <Card>
        <CardTitle>Workspace tasks</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium">Assignee</th>
                <th className="pb-3 font-medium">Priority</th>
                <th className="pb-3 font-medium">Due</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={6}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((task) => (
                <tr
                  key={task.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3">
                    <p className="font-medium">{task.title}</p>
                    <Link
                      className="text-xs text-teal-700 dark:text-teal-300"
                      href={`/app/projects/${task.project_id}`}
                    >
                      Open project
                    </Link>
                  </td>
                  <td className="py-3">
                    <select
                      className="w-full max-w-[200px] rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-sm dark:border-stone-700 dark:bg-stone-950"
                      value={task.assignee_id ?? ""}
                      disabled={assign.isPending}
                      onChange={(e) =>
                        assign.mutate({ id: task.id, assignee_id: e.target.value })
                      }
                    >
                      <option value="">Unassigned</option>
                      {(users?.items ?? []).map((m) => (
                        <option key={m.id} value={m.user_id}>
                          {memberLabel.get(m.user_id) ?? m.user_id}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-3 capitalize">{task.priority}</td>
                  <td className="py-3 text-stone-500">
                    {task.due_date
                      ? new Date(task.due_date).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="py-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="py-3">
                    {task.status !== "done" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => complete.mutate(task.id)}
                      >
                        Complete
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && (data?.items.length ?? 0) === 0 && (
                <tr>
                  <td className="py-6" colSpan={6}>
                    <EmptyState
                      title="No tasks yet"
                      description="Open a project to create and assign work to field officers."
                      actionLabel="Browse projects"
                      actionHref="/app/projects"
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
