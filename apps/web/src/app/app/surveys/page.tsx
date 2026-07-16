"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

export default function SurveysPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["surveys"],
    queryFn: () => api.listSurveys(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createSurvey({
        name,
        description: description || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["surveys"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const publish = useMutation({
    mutationFn: (id: string) => api.updateSurvey(id, { status: "published", publish: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["surveys"] }),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Surveys</h1>
        <p className="mt-2 text-stone-500">
          Build JSON-schema forms and collect field responses.
        </p>
      </div>

      <Card>
        <CardTitle>Create survey</CardTitle>
        <CardDescription>
          Starts with a starter schema you can refine after creation.
        </CardDescription>
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
              {create.isPending ? "Creating…" : "Create survey"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>All surveys</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <EmptyState
              title="No surveys yet"
              description="Create a draft survey to start collecting field responses."
            />
          )}
          {data?.items.map((s) => (
            <div
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div>
                <Link
                  href={`/app/surveys/${s.id}`}
                  className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                >
                  {s.name}
                </Link>
                <p className="text-xs text-stone-500">
                  {s.code} · v{s.current_version}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={s.status} />
                {s.status !== "published" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={publish.isPending}
                    onClick={() => publish.mutate(s.id)}
                  >
                    Publish
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
