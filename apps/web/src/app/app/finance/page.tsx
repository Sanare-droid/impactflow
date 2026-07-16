"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function FinancePage() {
  const qc = useQueryClient();
  const [txnType, setTxnType] = useState("expense");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [grantId, setGrantId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: grants } = useQuery({
    queryKey: ["grants"],
    queryFn: () => api.listGrants(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["finance-transactions"],
    queryFn: () => api.listTransactions(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createTransaction({
        transaction_type: txnType,
        amount: Number(amount),
        transaction_date: new Date().toISOString().slice(0, 10),
        description: description || undefined,
        grant_id: grantId || undefined,
        currency: "USD",
        status: "posted",
      }),
    onSuccess: async () => {
      setAmount("");
      setDescription("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["finance-transactions"] });
      await qc.invalidateQueries({ queryKey: ["grants"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Finance</h1>
        <p className="mt-2 text-stone-500">
          Income, expenses, and commitments against grants and budgets.
        </p>
      </div>

      <Card>
        <CardTitle>Post transaction</CardTitle>
        <CardDescription>
          Income against a grant updates received totals automatically.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="type">Type</Label>
            <select
              id="type"
              className="flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-950"
              value={txnType}
              onChange={(e) => setTxnType(e.target.value)}
            >
              <option value="income">Income</option>
              <option value="expense">Expense</option>
              <option value="commitment">Commitment</option>
              <option value="transfer">Transfer</option>
            </select>
          </div>
          <div>
            <Label htmlFor="amount">Amount</Label>
            <Input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
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
              {create.isPending ? "Posting…" : "Post transaction"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Ledger</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Date</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Amount</th>
                <th className="pb-3 font-medium">Description</th>
                <th className="pb-3 font-medium">Status</th>
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
              {data?.items.map((txn) => (
                <tr
                  key={txn.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3">
                    {new Date(txn.transaction_date).toLocaleDateString()}
                  </td>
                  <td className="py-3 capitalize">{txn.transaction_type}</td>
                  <td className="py-3">
                    {txn.currency} {Number(txn.amount).toLocaleString()}
                  </td>
                  <td className="py-3 text-stone-600 dark:text-stone-300">
                    {txn.description || "—"}
                  </td>
                  <td className="py-3">
                    <StatusBadge status={txn.status} />
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
