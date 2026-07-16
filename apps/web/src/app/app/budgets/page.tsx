"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function BudgetsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [grantId, setGrantId] = useState("");
  const [category, setCategory] = useState("Personnel");
  const [lineAmount, setLineAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: grants } = useQuery({
    queryKey: ["grants"],
    queryFn: () => api.listGrants(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["budgets"],
    queryFn: () => api.listBudgets(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createBudget({
        name,
        grant_id: grantId || undefined,
        status: "draft",
        currency: "USD",
        lines: lineAmount
          ? [{ category, amount: Number(lineAmount), sort_order: 0 }]
          : [],
      }),
    onSuccess: async () => {
      setName("");
      setLineAmount("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["budgets"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Budgets</h1>
        <p className="mt-2 text-stone-500">
          Structured budgets with line items for grants and projects.
        </p>
      </div>

      <Card>
        <CardTitle>Create budget</CardTitle>
        <CardDescription>Optionally attach to a grant and seed one line item.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Budget name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="grant">Grant (optional)</Label>
            <select
              id="grant"
              className="flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-950"
              value={grantId}
              onChange={(e) => setGrantId(e.target.value)}
            >
              <option value="">None</option>
              {grants?.items.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="category">First line category</Label>
            <Input
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="amount">First line amount</Label>
            <Input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              value={lineAmount}
              onChange={(e) => setLineAmount(e.target.value)}
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create budget"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Budget register</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((budget) => (
            <div
              key={budget.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-800"
            >
              <div>
                <p className="font-medium">{budget.name}</p>
                <p className="text-xs text-stone-500">
                  {budget.currency} {Number(budget.total_amount).toLocaleString()}
                  {budget.fiscal_year ? ` · FY${budget.fiscal_year}` : ""}
                </p>
              </div>
              <StatusBadge status={budget.status} />
            </div>
          ))}
          {!isLoading && data?.items.length === 0 && (
            <p className="text-sm text-stone-400">No budgets yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
