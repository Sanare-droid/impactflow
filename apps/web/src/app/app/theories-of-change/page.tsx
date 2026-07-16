"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function TheoriesOfChangePage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [problem, setProblem] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["theories-of-change"],
    queryFn: () => api.listTheoriesOfChange(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createTheoryOfChange({
        name,
        goal_statement: goal || undefined,
        problem_statement: problem || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setGoal("");
      setProblem("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["theories-of-change"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Theory of Change</h1>
        <p className="mt-2 text-stone-500">Causal pathways from problem to impact.</p>
      </div>

      <Card>
        <CardTitle>New theory of change</CardTitle>
        <CardDescription>Link later to programs, projects, and logframes.</CardDescription>
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
        <CardTitle>Theories of change</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Goal</th>
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
              {data?.items.map((toc) => (
                <tr
                  key={toc.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{toc.name}</td>
                  <td className="py-3 font-mono text-xs">{toc.code}</td>
                  <td className="max-w-xs truncate py-3 text-stone-500">
                    {toc.goal_statement || "—"}
                  </td>
                  <td className="py-3">
                    <StatusBadge status={toc.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
