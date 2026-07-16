"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function GrantsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [donorId, setDonorId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState<string | null>(null);

  const { data: donors } = useQuery({
    queryKey: ["donors"],
    queryFn: () => api.listDonors(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["grants"],
    queryFn: () => api.listGrants(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createGrant({
        name,
        donor_id: donorId,
        amount_awarded: Number(amount || 0),
        currency,
        status: "pipeline",
      }),
    onSuccess: async () => {
      setName("");
      setAmount("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["grants"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const activate = useMutation({
    mutationFn: (id: string) => api.updateGrant(id, { status: "active" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants"] }),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Grants</h1>
        <p className="mt-2 text-stone-500">
          Funding agreements linked to donors, programs, and projects.
        </p>
      </div>

      <Card>
        <CardTitle>Create grant</CardTitle>
        <CardDescription>Start in pipeline, then move to awarded/active.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="md:col-span-2">
            <Label htmlFor="name">Grant name</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="donor">Donor</Label>
            <select
              id="donor"
              required
              className="flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-950"
              value={donorId}
              onChange={(e) => setDonorId(e.target.value)}
            >
              <option value="">Select donor…</option>
              {donors?.items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="amount">Amount awarded</Label>
              <Input
                id="amount"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="currency">Currency</Label>
              <Input
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                maxLength={3}
              />
            </div>
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending || !donorId}>
              {create.isPending ? "Creating…" : "Create grant"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Grant portfolio</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Awarded</th>
                <th className="pb-3 font-medium">Received</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Actions</th>
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
              {data?.items.map((grant) => (
                <tr
                  key={grant.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{grant.name}</td>
                  <td className="py-3 font-mono text-xs">{grant.code}</td>
                  <td className="py-3">
                    {grant.currency} {Number(grant.amount_awarded).toLocaleString()}
                  </td>
                  <td className="py-3">
                    {grant.currency} {Number(grant.amount_received).toLocaleString()}
                  </td>
                  <td className="py-3">
                    <StatusBadge status={grant.status} />
                  </td>
                  <td className="py-3">
                    {grant.status !== "active" && grant.status !== "closed" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => activate.mutate(grant.id)}
                      >
                        Activate
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
