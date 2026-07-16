"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function MonitoringPage() {
  const qc = useQueryClient();
  const [indicatorId, setIndicatorId] = useState("");
  const [actualValue, setActualValue] = useState("");
  const [reportingDate, setReportingDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: indicators } = useQuery({
    queryKey: ["indicators"],
    queryFn: () => api.listIndicators(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["monitoring-results"],
    queryFn: () => api.listMonitoringResults(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createMonitoringResult({
        indicator_id: indicatorId,
        reporting_date: reportingDate,
        actual_value: actualValue ? Number(actualValue) : undefined,
        notes: notes || undefined,
        status: "submitted",
      }),
    onSuccess: async () => {
      setActualValue("");
      setNotes("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["monitoring-results"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const verify = useMutation({
    mutationFn: (id: string) => api.updateMonitoringResult(id, { status: "verified" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["monitoring-results"] });
    },
  });

  const indicatorName = (id: string) =>
    indicators?.items.find((i) => i.id === id)?.code ?? id.slice(0, 8);

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Monitoring</h1>
        <p className="mt-2 text-stone-500">Record actuals against indicators and verify submissions.</p>
      </div>

      <Card>
        <CardTitle>Record result</CardTitle>
        <CardDescription>Submit a monitoring value for an indicator.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="md:col-span-2">
            <Label htmlFor="indicator">Indicator</Label>
            <select
              id="indicator"
              required
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={indicatorId}
              onChange={(e) => setIndicatorId(e.target.value)}
            >
              <option value="">Select…</option>
              {indicators?.items.map((ind) => (
                <option key={ind.id} value={ind.id}>
                  {ind.code} — {ind.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="date">Reporting date</Label>
            <Input
              id="date"
              type="date"
              required
              value={reportingDate}
              onChange={(e) => setReportingDate(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="actual">Actual value</Label>
            <Input
              id="actual"
              type="number"
              value={actualValue}
              onChange={(e) => setActualValue(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="notes">Notes</Label>
            <Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending || !indicatorId}>
              {create.isPending ? "Saving…" : "Submit result"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Results ledger</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Indicator</th>
                <th className="pb-3 font-medium">Date</th>
                <th className="pb-3 font-medium">Actual</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={5}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-mono text-xs">{indicatorName(row.indicator_id)}</td>
                  <td className="py-3">{row.reporting_date}</td>
                  <td className="py-3">{row.actual_value ?? row.qualitative_value ?? "—"}</td>
                  <td className="py-3">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="py-3 text-right">
                    {row.status !== "verified" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => verify.mutate(row.id)}
                        disabled={verify.isPending}
                      >
                        Verify
                      </Button>
                    )}
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
