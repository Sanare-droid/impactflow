"use client";

import Link from "next/link";
import { FormEvent, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

const selectClassName =
  "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-950";

function ProjectsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const programIdFilter = searchParams.get("program_id") ?? undefined;
  const qc = useQueryClient();

  const [programId, setProgramId] = useState(programIdFilter ?? "");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["projects", programIdFilter ?? "all"],
    queryFn: () => api.listProjects({ program_id: programIdFilter }),
  });

  const { data: programs } = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createProject({
        program_id: programId,
        name,
        code: code || undefined,
        status: "planning",
        priority: "medium",
      }),
    onSuccess: async (project) => {
      setName("");
      setCode("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["projects"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      router.push(`/app/projects/${project.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-2 text-stone-500">
            Delivery units across programs
            {programIdFilter ? " · filtered by program" : ""}.
          </p>
        </div>
        <Link href="/app/programs" className="text-sm text-teal-700 dark:text-teal-300">
          View programs →
        </Link>
      </div>

      <Card>
        <CardTitle>Create project</CardTitle>
        <CardDescription>Pick a program, then open the project to manage delivery work.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="program">Program</Label>
            <select
              id="program"
              required
              className={selectClassName}
              value={programId}
              onChange={(e) => setProgramId(e.target.value)}
            >
              <option value="">Select program…</option>
              {(programs?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            {(programs?.items.length ?? 0) === 0 ? (
              <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                No programs yet.{" "}
                <Link href="/app/programs" className="underline">
                  Create a program
                </Link>{" "}
                first.
              </p>
            ) : null}
          </div>
          <div>
            <Label htmlFor="code">Code (optional)</Label>
            <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending || !programId}>
              {create.isPending ? "Creating…" : "Create project"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Project list</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Priority</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={4}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((project) => (
                <tr
                  key={project.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3">
                    <Link
                      className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                      href={`/app/projects/${project.id}`}
                    >
                      {project.name}
                    </Link>
                  </td>
                  <td className="py-3 font-mono text-xs">{project.code}</td>
                  <td className="py-3 capitalize">{project.priority}</td>
                  <td className="py-3">
                    <StatusBadge status={project.status} />
                  </td>
                </tr>
              ))}
              {!isLoading && data?.items.length === 0 && (
                <tr>
                  <td className="py-6" colSpan={4}>
                    <EmptyState
                      title="No projects yet"
                      description="Create a project above, or start from a program."
                      actionLabel="Go to programs"
                      actionHref="/app/programs"
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

export default function ProjectsPage() {
  return (
    <Suspense fallback={<div className="text-sm text-stone-500">Loading projects…</div>}>
      <ProjectsContent />
    </Suspense>
  );
}
