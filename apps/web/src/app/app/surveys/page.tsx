"use client";

import { FeatureGate } from "@/components/feature-gate";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Download, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

export default function SurveysPage() {
  return (
    <FeatureGate feature="surveys" fallbackTitle="Surveys are not on your plan">
      <SurveysInner />
    </FeatureGate>
  );
}

function SurveysInner() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["surveys"],
    queryFn: () => api.listSurveys(),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["surveys"] });

  const create = useMutation({
    mutationFn: () =>
      api.createSurvey({
        name,
        description: description || undefined,
        category: category || undefined,
        status: "draft",
      }),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setCategory("");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const publish = useMutation({
    mutationFn: (id: string) => api.updateSurvey(id, { status: "published", publish: true }),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const clone = useMutation({
    mutationFn: (id: string) => api.cloneSurvey(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.archiveSurvey(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const exportJson = async (id: string, code: string) => {
    setBusyId(id);
    setError(null);
    try {
      const payload = await api.exportSurveySchema(id);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${code}-schema.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusyId(null);
    }
  };

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
          className="mt-4 grid gap-3 md:grid-cols-3"
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
            <Label htmlFor="category">Category</Label>
            <Input
              id="category"
              placeholder="e.g. household, monitoring"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="md:col-span-3 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-3">
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
              actionLabel="Create survey"
              actionHref="/app/surveys"
            />
          )}
          {data?.items.map((s) => (
            <div
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-100 px-4 py-3 dark:border-stone-900"
            >
              <div className="min-w-0">
                <Link
                  href={`/app/surveys/${s.id}`}
                  className="font-medium text-teal-800 hover:underline dark:text-teal-300"
                >
                  {s.name}
                </Link>
                <p className="text-xs text-stone-500">
                  {s.code} · v{s.current_version}
                  {s.category ? ` · ${s.category}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={s.status} />
                <Link
                  href={`/app/surveys/${s.id}`}
                  className="inline-flex h-8 items-center rounded-md border border-stone-200 px-3 text-xs font-medium transition-colors hover:bg-stone-50 dark:border-stone-700 dark:hover:bg-stone-900"
                >
                  Open
                </Link>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={clone.isPending}
                  onClick={() => clone.mutate(s.id)}
                  title="Clone survey"
                >
                  <Copy className="h-3.5 w-3.5" /> Clone
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busyId === s.id}
                  onClick={() => exportJson(s.id, s.code)}
                  title="Export schema JSON"
                >
                  <Download className="h-3.5 w-3.5" /> Export
                </Button>
                {s.status !== "published" && s.status !== "archived" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={publish.isPending}
                    onClick={() => publish.mutate(s.id)}
                  >
                    Publish
                  </Button>
                )}
                {s.status !== "archived" && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={archive.isPending}
                    onClick={() => archive.mutate(s.id)}
                    title="Archive survey"
                  >
                    <FileText className="h-3.5 w-3.5" /> Archive
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
