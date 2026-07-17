"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

const selectClassName =
  "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950";

export default function TheoriesOfChangePage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [problem, setProblem] = useState("");
  const [programId, setProgramId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["theories-of-change"],
    queryFn: () => api.listTheoriesOfChange(),
  });

  const { data: programs } = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createTheoryOfChange({
        name,
        goal_statement: goal || undefined,
        problem_statement: problem || undefined,
        program_id: programId || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setGoal("");
      setProblem("");
      setProgramId("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["theories-of-change"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const programName = (id?: string | null) =>
    programs?.items.find((p) => p.id === id)?.name;

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Theory of Change</h1>
        <p className="mt-2 text-stone-500">Causal pathways from problem to impact.</p>
      </div>

      <Card>
        <CardTitle>New theory of change</CardTitle>
        <CardDescription>Optionally link to a program for delivery alignment.</CardDescription>
        <form
          className="mt-4 grid gap-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="program">Program (optional)</Label>
            <select
              id="program"
              className={selectClassName}
              value={programId}
              onChange={(e) => setProgramId(e.target.value)}
            >
              <option value="">None</option>
              {(programs?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="problem">Problem statement</Label>
            <Input id="problem" value={problem} onChange={(e) => setProblem(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="goal">Goal / impact statement</Label>
            <Input id="goal" value={goal} onChange={(e) => setGoal(e.target.value)} />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Saved theories</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {(data?.items ?? []).map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium">{item.name}</p>
                <StatusBadge status={item.status} />
              </div>
              {item.problem_statement ? (
                <p className="mt-1 text-sm text-stone-500">{item.problem_statement}</p>
              ) : null}
              {item.program_id ? (
                <Link
                  href={`/app/programs/${item.program_id}`}
                  className="mt-2 inline-block text-xs text-teal-700 dark:text-teal-300"
                >
                  {programName(item.program_id) ?? "Linked program"} →
                </Link>
              ) : null}
            </div>
          ))}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No theories of change yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
