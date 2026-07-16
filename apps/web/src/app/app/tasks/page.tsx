"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export default function TasksPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["tasks", "all"],
    queryFn: () => api.listTasks(),
  });

  const complete = useMutation({
    mutationFn: (id: string) => api.updateTask(id, { status: "done" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Tasks</h1>
        <p className="mt-2 text-stone-500">
          Cross-project action items. Open a project to add detailed tasks.
        </p>
      </div>

      <Card>
        <CardTitle>Workspace tasks</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium">Priority</th>
                <th className="pb-3 font-medium">Due</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={5}>
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
                        Mark done
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && data?.items.length === 0 && (
                <tr>
                  <td className="py-6 text-stone-400" colSpan={5}>
                    No tasks yet.
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
