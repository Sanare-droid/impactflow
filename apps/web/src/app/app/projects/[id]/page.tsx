"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const qc = useQueryClient();

  const [activityName, setActivityName] = useState("");
  const [planName, setPlanName] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: activities } = useQuery({
    queryKey: ["activities", projectId],
    queryFn: () => api.listActivities(projectId),
  });

  const { data: workPlans } = useQuery({
    queryKey: ["work-plans", projectId],
    queryFn: () => api.listWorkPlans(projectId),
  });

  const { data: tasks } = useQuery({
    queryKey: ["tasks", projectId],
    queryFn: () => api.listTasks({ project_id: projectId }),
  });

  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["activities", projectId] }),
      qc.invalidateQueries({ queryKey: ["work-plans", projectId] }),
      qc.invalidateQueries({ queryKey: ["tasks", projectId] }),
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] }),
    ]);
  };

  const createActivity = useMutation({
    mutationFn: () =>
      api.createActivity({
        project_id: projectId,
        name: activityName,
        status: "planned",
      }),
    onSuccess: async () => {
      setActivityName("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const createPlan = useMutation({
    mutationFn: () =>
      api.createWorkPlan({
        project_id: projectId,
        name: planName,
        status: "active",
      }),
    onSuccess: async () => {
      setPlanName("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const createTask = useMutation({
    mutationFn: () =>
      api.createTask({
        project_id: projectId,
        title: taskTitle,
        status: "todo",
        priority: "medium",
      }),
    onSuccess: async () => {
      setTaskTitle("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const completeTask = useMutation({
    mutationFn: (id: string) => api.updateTask(id, { status: "done" }),
    onSuccess: invalidate,
  });

  if (isLoading || !project) {
    return <div className="text-sm text-stone-500">Loading project…</div>;
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <Link href="/app/projects" className="text-sm text-teal-700 dark:text-teal-300">
          ← Projects
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            {project.name}
          </h1>
          <StatusBadge status={project.status} />
        </div>
        <p className="mt-2 text-stone-500">
          {project.code}
          {project.location ? ` · ${project.location}` : ""}
          {project.country_code ? ` · ${project.country_code}` : ""}
        </p>
      </div>

      {error && (
        <Card className="border-rose-200 text-rose-700 dark:border-rose-900 dark:text-rose-300">
          {error}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardTitle>Activities</CardTitle>
          <CardDescription>Work packages under this project.</CardDescription>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createActivity.mutate();
            }}
          >
            <div>
              <Label htmlFor="activity">New activity</Label>
              <Input
                id="activity"
                required
                value={activityName}
                onChange={(e) => setActivityName(e.target.value)}
              />
            </div>
            <Button type="submit" size="sm" disabled={createActivity.isPending}>
              Add activity
            </Button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">
            {activities?.items.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between rounded-lg bg-stone-50 px-3 py-2 dark:bg-stone-900"
              >
                <span>{item.name}</span>
                <StatusBadge status={item.status} />
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>Work plans</CardTitle>
          <CardDescription>Time-boxed delivery plans.</CardDescription>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createPlan.mutate();
            }}
          >
            <div>
              <Label htmlFor="plan">New work plan</Label>
              <Input
                id="plan"
                required
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
              />
            </div>
            <Button type="submit" size="sm" disabled={createPlan.isPending}>
              Add work plan
            </Button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">
            {workPlans?.items.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between rounded-lg bg-stone-50 px-3 py-2 dark:bg-stone-900"
              >
                <span>{item.name}</span>
                <StatusBadge status={item.status} />
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>Tasks</CardTitle>
          <CardDescription>Assignable action items.</CardDescription>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createTask.mutate();
            }}
          >
            <div>
              <Label htmlFor="task">New task</Label>
              <Input
                id="task"
                required
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
              />
            </div>
            <Button type="submit" size="sm" disabled={createTask.isPending}>
              Add task
            </Button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">
            {tasks?.items.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-2 rounded-lg bg-stone-50 px-3 py-2 dark:bg-stone-900"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{item.title}</p>
                  <StatusBadge status={item.status} />
                </div>
                {item.status !== "done" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => completeTask.mutate(item.id)}
                  >
                    Done
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
