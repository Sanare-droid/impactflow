"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function CommunitiesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [communityType, setCommunityType] = useState("village");
  const [region, setRegion] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["communities"],
    queryFn: () => api.listCommunities(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createCommunity({
        name,
        community_type: communityType,
        region: region || undefined,
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setRegion("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["communities"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Communities</h1>
        <p className="mt-2 text-stone-500">Villages, camps, wards, and other localities.</p>
      </div>

      <Card>
        <CardTitle>Add community</CardTitle>
        <CardDescription>Geographic and administrative targeting units.</CardDescription>
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
              value={communityType}
              onChange={(e) => setCommunityType(e.target.value)}
            >
              <option value="village">Village</option>
              <option value="camp">Camp</option>
              <option value="ward">Ward</option>
              <option value="district">District</option>
              <option value="settlement">Settlement</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="region">Region</Label>
            <Input id="region" value={region} onChange={(e) => setRegion(e.target.value)} />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create community"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Community directory</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Region</th>
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
              {data?.items.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{c.name}</td>
                  <td className="py-3 font-mono text-xs">{c.code}</td>
                  <td className="py-3 capitalize">{c.community_type}</td>
                  <td className="py-3">{c.region || "—"}</td>
                  <td className="py-3">
                    <StatusBadge status={c.status} />
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
