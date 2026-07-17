"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const selectClassName =
  "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-950";

function paramId(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = paramId(params.id);
  const router = useRouter();
  const qc = useQueryClient();

  const [activityName, setActivityName] = useState("");
  const [planName, setPlanName] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const {
    data: project,
    isLoading,
    isError,
    error: loadError,
  } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    enabled: Boolean(projectId),
  });

  const { data: activities } = useQuery({
    queryKey: ["activities", projectId],
    queryFn: () => api.listActivities(projectId),
    enabled: Boolean(projectId),
  });

  const { data: workPlans } = useQuery({
    queryKey: ["work-plans", projectId],
    queryFn: () => api.listWorkPlans(projectId),
    enabled: Boolean(projectId),
  });

  const { data: tasks } = useQuery({
    queryKey: ["tasks", projectId],
    queryFn: () => api.listTasks({ project_id: projectId }),
    enabled: Boolean(projectId),
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers({ page_size: 100 }),
  });

  const members = useMemo(
    () => (users?.items ?? []).filter((m) => m.status === "active" && m.user),
    [users],
  );

  const memberLabel = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of members) {
      if (!m.user) continue;
      map.set(
        m.user_id,
        `${m.user.first_name} ${m.user.last_name}`.trim() || m.user.email,
      );
    }
    return map;
  }, [members]);

  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["activities", projectId] }),
      qc.invalidateQueries({ queryKey: ["work-plans", projectId] }),
      qc.invalidateQueries({ queryKey: ["tasks", projectId] }),
      qc.invalidateQueries({ queryKey: ["tasks", "all"] }),
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
        assignee_id: assigneeId || null,
        due_date: dueDate || null,
      }),
    onSuccess: async () => {
      setTaskTitle("");
      setAssigneeId("");
      setDueDate("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const completeTask = useMutation({
    mutationFn: (id: string) => api.updateTask(id, { status: "done" }),
    onSuccess: invalidate,
  });

  const assignTask = useMutation({
    mutationFn: ({ id, nextAssignee }: { id: string; nextAssignee: string }) =>
      api.updateTask(id, { assignee_id: nextAssignee || null }),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading) {
    return <div className="text-sm text-stone-500">Loading project…</div>;
  }

  if (isError || !project) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-rose-600">
          {(loadError as Error | undefined)?.message || "Unable to load this project."}
        </p>
        <Button variant="secondary" onClick={() => router.push("/app/projects")}>
          Back to projects
        </Button>
      </div>
    );
  }

  const programHref = project.program_id
    ? `/app/programs/${project.program_id}`
    : "/app/programs";

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href={programHref} className="text-teal-700 dark:text-teal-300">
            ← Program
          </Link>
          <Link href="/app/projects" className="text-stone-500 hover:text-teal-700">
            All projects
          </Link>
        </div>
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

      {/* Tasks first — this is the field assignment surface */}
      <Card>
        <CardTitle>Tasks</CardTitle>
        <CardDescription>
          Create work and assign a teammate. Assigned tasks sync to their mobile field app.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createTask.mutate();
          }}
        >
          <div className="md:col-span-2 lg:col-span-2">
            <Label htmlFor="task">Task title</Label>
            <Input
              id="task"
              required
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="e.g. Visit household for baseline survey"
            />
          </div>
          <div>
            <Label htmlFor="assignee">Assignee</Label>
            <select
              id="assignee"
              className={selectClassName}
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.id} value={m.user_id}>
                  {m.user
                    ? `${m.user.first_name} ${m.user.last_name}`.trim() || m.user.email
                    : m.user_id}
                  {m.role?.slug === "field_officer" ? " · Field" : ""}
                </option>
              ))}
            </select>
            {members.length === 0 ? (
              <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                No teammates yet.{" "}
                <Link href="/app/users" className="underline">
                  Invite users
                </Link>{" "}
                first.
              </p>
            ) : null}
          </div>
          <div>
            <Label htmlFor="due">Due date</Label>
            <Input
              id="due"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="md:col-span-2 lg:col-span-4">
            <Button type="submit" disabled={createTask.isPending}>
              {createTask.isPending ? "Creating…" : "Create & assign task"}
            </Button>
          </div>
        </form>

        <div className="mt-6 space-y-3">
          {(tasks?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">
              No tasks yet. Create one above and pick an assignee for mobile sync.
            </p>
          )}
          {tasks?.items.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-3 rounded-xl border border-stone-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:border-stone-800"
            >
              <div className="min-w-0">
                <p className="font-medium">{item.title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StatusBadge status={item.status} />
                  <span className="text-xs text-stone-500">
                    {item.assignee_id
                      ? memberLabel.get(item.assignee_id) ?? "Assigned"
                      : "Unassigned"}
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-xs dark:border-stone-700 dark:bg-stone-950"
                  value={item.assignee_id ?? ""}
                  disabled={assignTask.isPending}
                  onChange={(e) =>
                    assignTask.mutate({ id: item.id, nextAssignee: e.target.value })
                  }
                >
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.id} value={m.user_id}>
                      {memberLabel.get(m.user_id) ?? m.user_id}
                    </option>
                  ))}
                </select>
                {item.status !== "done" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => completeTask.mutate(item.id)}
                  >
                    Done
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Activities</CardTitle>
          <CardDescription>Optional work packages under this project.</CardDescription>
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
          <CardDescription>Optional time-boxed delivery plans.</CardDescription>
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
      </div>
    </div>
  );
}
