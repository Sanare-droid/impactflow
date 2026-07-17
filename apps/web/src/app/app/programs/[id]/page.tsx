"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

function paramId(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export default function ProgramDetailPage() {
  const params = useParams<{ id: string }>();
  const programId = paramId(params.id);
  const router = useRouter();
  const qc = useQueryClient();
  const [projectName, setProjectName] = useState("");
  const [projectCode, setProjectCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const {
    data: program,
    isLoading,
    isError,
    error: loadError,
  } = useQuery({
    queryKey: ["program", programId],
    queryFn: () => api.getProgram(programId),
    enabled: Boolean(programId),
  });

  const { data: projects } = useQuery({
    queryKey: ["projects", programId],
    queryFn: () => api.listProjects({ program_id: programId }),
    enabled: Boolean(programId),
  });

  const createProject = useMutation({
    mutationFn: () =>
      api.createProject({
        program_id: programId,
        name: projectName,
        code: projectCode || undefined,
        status: "planning",
      }),
    onSuccess: async (project) => {
      setProjectName("");
      setProjectCode("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["projects", programId] });
      await qc.invalidateQueries({ queryKey: ["projects", "all"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      router.push(`/app/projects/${project.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    createProject.mutate();
  }

  if (isLoading) {
    return <div className="text-sm text-stone-500">Loading program…</div>;
  }

  if (isError || !program) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-rose-600">
          {(loadError as Error | undefined)?.message || "Unable to load this program."}
        </p>
        <Link href="/app/programs" className="text-sm text-teal-700 dark:text-teal-300">
          ← Back to programs
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <Link href="/app/programs" className="text-sm text-teal-700 dark:text-teal-300">
          ← Programs
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            {program.name}
          </h1>
          <StatusBadge status={program.status} />
        </div>
        <p className="mt-2 text-stone-500">
          {program.code}
          {program.goal ? ` · ${program.goal}` : ""}
        </p>
      </div>

      <Card>
        <CardTitle>Add project</CardTitle>
        <CardDescription>
          After you create a project you will open its page to create and assign tasks.
        </CardDescription>
        <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="pname">Project name</Label>
            <Input
              id="pname"
              required
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="pcode">Code</Label>
            <Input
              id="pcode"
              value={projectCode}
              onChange={(e) => setProjectCode(e.target.value)}
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={createProject.isPending}>
              {createProject.isPending ? "Creating…" : "Create project"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Projects</CardTitle>
        <CardDescription>
          Open a project to create tasks and assign field officers.
        </CardDescription>
        <div className="mt-4 space-y-3">
          {projects?.items.map((project) => (
            <Link
              key={project.id}
              href={`/app/projects/${project.id}`}
              className="flex items-center justify-between rounded-xl border border-stone-100 px-4 py-3 transition hover:border-teal-200 dark:border-stone-800 dark:hover:border-teal-900"
            >
              <div>
                <p className="font-medium">{project.name}</p>
                <p className="text-xs text-stone-500">
                  {project.code} · Open to create & assign tasks
                </p>
              </div>
              <StatusBadge status={project.status} />
            </Link>
          ))}
          {projects?.items.length === 0 && (
            <p className="text-sm text-stone-400">No projects in this program yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
