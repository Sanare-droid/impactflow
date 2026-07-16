"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function IndicatorsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [level, setLevel] = useState("outcome");
  const [unit, setUnit] = useState("");
  const [baseline, setBaseline] = useState("");
  const [periodLabel, setPeriodLabel] = useState("");
  const [targetValue, setTargetValue] = useState("");
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["indicators"],
    queryFn: () => api.listIndicators(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createIndicator({
        name,
        level,
        unit: unit || undefined,
        baseline_value: baseline ? Number(baseline) : undefined,
        measure_type: "quantitative",
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setUnit("");
      setBaseline("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["indicators"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const addTarget = useMutation({
    mutationFn: () =>
      api.addIndicatorTarget(selectedIndicator, {
        period_label: periodLabel,
        target_value: Number(targetValue || 0),
      }),
    onSuccess: async () => {
      setPeriodLabel("");
      setTargetValue("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["indicators"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Indicators</h1>
        <p className="mt-2 text-stone-500">Define measures, baselines, and period targets.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>New indicator</CardTitle>
          <CardDescription>Codes are generated uniquely per organization.</CardDescription>
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
                <option value="process">Process</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="unit">Unit</Label>
                <Input id="unit" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="%" />
              </div>
              <div>
                <Label htmlFor="baseline">Baseline</Label>
                <Input
                  id="baseline"
                  type="number"
                  value={baseline}
                  onChange={(e) => setBaseline(e.target.value)}
                />
              </div>
            </div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create indicator"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Add target</CardTitle>
          <CardDescription>Period targets linked to an indicator.</CardDescription>
          <form
            className="mt-4 grid gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              addTarget.mutate();
            }}
          >
            <div>
              <Label htmlFor="ind">Indicator</Label>
              <select
                id="ind"
                required
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={selectedIndicator}
                onChange={(e) => setSelectedIndicator(e.target.value)}
              >
                <option value="">Select…</option>
                {data?.items.map((ind) => (
                  <option key={ind.id} value={ind.id}>
                    {ind.code} — {ind.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="period">Period label</Label>
              <Input
                id="period"
                required
                value={periodLabel}
                onChange={(e) => setPeriodLabel(e.target.value)}
                placeholder="FY2026 Q1"
              />
            </div>
            <div>
              <Label htmlFor="target">Target value</Label>
              <Input
                id="target"
                type="number"
                required
                value={targetValue}
                onChange={(e) => setTargetValue(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={addTarget.isPending || !selectedIndicator}>
              {addTarget.isPending ? "Saving…" : "Add target"}
            </Button>
          </form>
        </Card>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <Card>
        <CardTitle>Indicator register</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Level</th>
                <th className="pb-3 font-medium">Baseline</th>
                <th className="pb-3 font-medium">Targets</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={6}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((ind) => (
                <tr
                  key={ind.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-mono text-xs">{ind.code}</td>
                  <td className="py-3 font-medium">{ind.name}</td>
                  <td className="py-3 capitalize">{ind.level}</td>
                  <td className="py-3">
                    {ind.baseline_value ?? "—"}
                    {ind.unit ? ` ${ind.unit}` : ""}
                  </td>
                  <td className="py-3">{ind.targets?.length ?? 0}</td>
                  <td className="py-3">
                    <StatusBadge status={ind.status} />
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
