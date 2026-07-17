"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function EvaluationsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [evaluationType, setEvaluationType] = useState("midline");
  const [objectives, setObjectives] = useState("");
  const [programId, setProgramId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["evaluations"],
    queryFn: () => api.listEvaluations(),
  });

  const { data: programs } = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createEvaluation({
        name,
        evaluation_type: evaluationType,
        objectives: objectives || undefined,
        program_id: programId || undefined,
        status: "planned",
      }),
    onSuccess: async () => {
      setName("");
      setObjectives("");
      setProgramId("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["evaluations"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Evaluations</h1>
        <p className="mt-2 text-stone-500">
          Baseline, midline, endline, and thematic evaluation studies.
        </p>
      </div>

      <Card>
        <CardTitle>Plan evaluation</CardTitle>
        <CardDescription>Capture objectives; add findings as the study progresses.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
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
            <Label htmlFor="type">Type</Label>
            <select
              id="type"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={evaluationType}
              onChange={(e) => setEvaluationType(e.target.value)}
            >
              <option value="baseline">Baseline</option>
              <option value="midline">Midline</option>
              <option value="endline">Endline</option>
              <option value="thematic">Thematic</option>
              <option value="impact">Impact</option>
              <option value="process">Process</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="objectives">Objectives</Label>
            <Input
              id="objectives"
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="program">Program (optional)</Label>
            <select
              id="program"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
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
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create evaluation"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Evaluation portfolio</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Program</th>
                <th className="pb-3 font-medium">Type</th>
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
              {data?.items.map((ev) => (
                <tr
                  key={ev.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{ev.name}</td>
                  <td className="py-3 text-sm text-stone-500">
                    {ev.program_id ? (
                      <Link
                        className="text-teal-700 dark:text-teal-300"
                        href={`/app/programs/${ev.program_id}`}
                      >
                        {programs?.items.find((p) => p.id === ev.program_id)?.name ?? "Program"}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="py-3 capitalize">{ev.evaluation_type}</td>
                  <td className="py-3">
                    <StatusBadge status={ev.status} />
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
