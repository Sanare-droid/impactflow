"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function DonorsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [donorType, setDonorType] = useState("foundation");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["donors"],
    queryFn: () => api.listDonors(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createDonor({
        name,
        donor_type: donorType,
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["donors"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Donors</h1>
        <p className="mt-2 text-stone-500">Funding partners and development agencies.</p>
      </div>

      <Card>
        <CardTitle>Add donor</CardTitle>
        <CardDescription>Unique codes are generated per organization.</CardDescription>
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
            <Input
              id="type"
              value={donorType}
              onChange={(e) => setDonorType(e.target.value)}
              placeholder="foundation, bilateral, multilateral…"
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create donor"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Donor directory</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
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
              {data?.items.map((donor) => (
                <tr
                  key={donor.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{donor.name}</td>
                  <td className="py-3 font-mono text-xs">{donor.code}</td>
                  <td className="py-3 capitalize">{donor.donor_type}</td>
                  <td className="py-3">
                    <StatusBadge status={donor.status} />
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
