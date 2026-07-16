"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function HouseholdsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [size, setSize] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: communities } = useQuery({
    queryKey: ["communities"],
    queryFn: () => api.listCommunities(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["households"],
    queryFn: () => api.listHouseholds(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createHousehold({
        name,
        community_id: communityId || undefined,
        household_size: size ? Number(size) : undefined,
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setSize("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["households"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const communityName = (id?: string | null) =>
    communities?.items.find((c) => c.id === id)?.name ?? "—";

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Households</h1>
        <p className="mt-2 text-stone-500">Family and household units for targeting and caseloads.</p>
      </div>

      <Card>
        <CardTitle>Register household</CardTitle>
        <CardDescription>Optionally link to a community locality.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Household name / label</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="community">Community</Label>
            <select
              id="community"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={communityId}
              onChange={(e) => setCommunityId(e.target.value)}
            >
              <option value="">None</option>
              {communities?.items.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="size">Household size</Label>
            <Input
              id="size"
              type="number"
              value={size}
              onChange={(e) => setSize(e.target.value)}
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create household"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Household register</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Community</th>
                <th className="pb-3 font-medium">Size</th>
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
              {data?.items.map((hh) => (
                <tr
                  key={hh.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{hh.name}</td>
                  <td className="py-3 font-mono text-xs">{hh.code}</td>
                  <td className="py-3">{communityName(hh.community_id)}</td>
                  <td className="py-3">{hh.household_size ?? "—"}</td>
                  <td className="py-3">
                    <StatusBadge status={hh.status} />
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
