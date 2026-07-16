"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function ProgramsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createProgram({
        name,
        code: code || undefined,
        description: description || undefined,
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setCode("");
      setDescription("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["programs"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Programs</h1>
        <p className="mt-2 text-stone-500">
          Portfolio containers for related projects and interventions.
        </p>
      </div>

      <Card>
        <CardTitle>Create program</CardTitle>
        <CardDescription>Codes are unique per organization.</CardDescription>
        <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="code">Code (optional)</Label>
            <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create program"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>All programs</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Projects</th>
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
              {data?.items.map((program) => (
                <tr
                  key={program.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3">
                    <Link
                      className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                      href={`/app/programs/${program.id}`}
                    >
                      {program.name}
                    </Link>
                    {program.description && (
                      <p className="mt-0.5 line-clamp-1 text-xs text-stone-500">
                        {program.description}
                      </p>
                    )}
                  </td>
                  <td className="py-3 font-mono text-xs">{program.code}</td>
                  <td className="py-3">
                    <StatusBadge status={program.status} />
                  </td>
                  <td className="py-3">
                    <Link
                      className="text-teal-700 hover:underline dark:text-teal-300"
                      href={`/app/projects?program_id=${program.id}`}
                    >
                      View projects
                    </Link>
                  </td>
                </tr>
              ))}
              {!isLoading && data?.items.length === 0 && (
                <tr>
                  <td className="py-6 text-stone-400" colSpan={4}>
                    No programs yet. Create your first portfolio above.
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
