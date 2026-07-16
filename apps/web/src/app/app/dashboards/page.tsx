"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function DashboardsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["saved-dashboards"],
    queryFn: () => api.listSavedDashboards(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createSavedDashboard({
        name,
        description: description || undefined,
        status: "active",
        widgets: [
          { id: "programs", type: "metric", metric: "programs_count" },
          { id: "indicators", type: "metric", metric: "active_indicators_count" },
          { id: "beneficiaries", type: "metric", metric: "active_beneficiaries_count" },
        ],
      }),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["saved-dashboards"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Dashboards</h1>
        <p className="mt-2 text-stone-500">Saved widget layouts for program and MEAL oversight.</p>
      </div>

      <Card>
        <CardTitle>Create dashboard</CardTitle>
        <CardDescription>Starts with a default delivery / MEAL / field widget set.</CardDescription>
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
            <Label htmlFor="desc">Description</Label>
            <Input
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create dashboard"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Saved dashboards</CardTitle>
        <div className="mt-4 space-y-4">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((d) => (
            <div
              key={d.id}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-100 pb-4 last:border-0 dark:border-stone-900"
            >
              <div>
                <p className="font-medium">{d.name}</p>
                <p className="text-xs text-stone-500">
                  {d.code} · {(d.widgets ?? []).length} widgets
                  {d.is_default ? " · default" : ""}
                </p>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
