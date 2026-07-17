"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Suspense } from "react";
import { api } from "@/lib/api";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

function ProjectsContent() {
  const searchParams = useSearchParams();
  const programId = searchParams.get("program_id") ?? undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["projects", programId ?? "all"],
    queryFn: () => api.listProjects({ program_id: programId }),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-2 text-stone-500">
            Delivery units across programs
            {programId ? " · filtered by program" : ""}.
          </p>
        </div>
        <Link href="/app/programs">
          <span className="text-sm text-teal-700 dark:text-teal-300">Manage via programs →</span>
        </Link>
      </div>

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
                      description="Create a program first, then add a project from the program page."
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
