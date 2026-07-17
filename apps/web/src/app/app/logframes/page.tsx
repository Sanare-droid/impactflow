"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function LogframesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [tocId, setTocId] = useState("");
  const [programId, setProgramId] = useState("");
  const [level, setLevel] = useState("outcome");
  const [statement, setStatement] = useState("");
  const [selectedLogframe, setSelectedLogframe] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["logframes"],
    queryFn: () => api.listLogframes(),
  });

  const { data: tocs } = useQuery({
    queryKey: ["theories-of-change"],
    queryFn: () => api.listTheoriesOfChange(),
  });

  const { data: programs } = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createLogframe({
        name,
        theory_of_change_id: tocId || undefined,
        program_id: programId || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setTocId("");
      setProgramId("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["logframes"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const addResult = useMutation({
    mutationFn: () =>
      api.addLogframeResult(selectedLogframe, {
        level,
        statement,
      }),
    onSuccess: async () => {
      setStatement("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["logframes"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Logframes</h1>
        <p className="mt-2 text-stone-500">Results frameworks with impact → outcome → output rows.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>New logframe</CardTitle>
          <CardDescription>Optionally link a theory of change.</CardDescription>
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
              <Label htmlFor="toc">Theory of Change</Label>
              <select
                id="toc"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={tocId}
                onChange={(e) => setTocId(e.target.value)}
              >
                <option value="">None</option>
                {tocs?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
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
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create logframe"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Add result row</CardTitle>
          <CardDescription>Impact, outcome, output, or activity statement.</CardDescription>
          <form
            className="mt-4 grid gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              addResult.mutate();
            }}
          >
            <div>
              <Label htmlFor="lf">Logframe</Label>
              <select
                id="lf"
                required
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={selectedLogframe}
                onChange={(e) => setSelectedLogframe(e.target.value)}
              >
                <option value="">Select…</option>
                {data?.items.map((lf) => (
                  <option key={lf.id} value={lf.id}>
                    {lf.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="level">Level</Label>
              <select
                id="level"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
              >
                <option value="impact">Impact</option>
                <option value="outcome">Outcome</option>
                <option value="output">Output</option>
                <option value="activity">Activity</option>
              </select>
            </div>
            <div>
              <Label htmlFor="statement">Statement</Label>
              <Input
                id="statement"
                required
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={addResult.isPending || !selectedLogframe}>
              {addResult.isPending ? "Saving…" : "Add row"}
            </Button>
          </form>
        </Card>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <Card>
        <CardTitle>Logframe directory</CardTitle>
        <div className="mt-4 space-y-6">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((lf) => (
            <div key={lf.id} className="border-b border-stone-100 pb-5 last:border-0 dark:border-stone-900">
              <div className="flex flex-wrap items-center gap-3">
                <p className="font-medium">{lf.name}</p>
                <span className="font-mono text-xs text-stone-500">{lf.code}</span>
                <StatusBadge status={lf.status} />
                {lf.program_id ? (
                  <Link
                    href={`/app/programs/${lf.program_id}`}
                    className="text-xs text-teal-700 dark:text-teal-300"
                  >
                    {programs?.items.find((p) => p.id === lf.program_id)?.name ?? "Program"} →
                  </Link>
                ) : null}
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                {(lf.results ?? []).length === 0 && (
                  <li className="text-stone-400">No result rows yet.</li>
                )}
                {(lf.results ?? []).map((row) => (
                  <li key={row.id} className="flex gap-3">
                    <span className="w-20 shrink-0 capitalize text-stone-500">{row.level}</span>
                    <span>{row.statement}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
