"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function NarrativesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [narrativeType, setNarrativeType] = useState("executive_summary");
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ai-narratives"],
    queryFn: () => api.listAiNarratives(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.generateAiNarrative({
        name,
        narrative_type: narrativeType,
        prompt: prompt || undefined,
      }),
    onSuccess: async () => {
      setName("");
      setPrompt("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["ai-narratives"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Narratives</h1>
        <p className="mt-2 text-stone-500">
          Generate donor updates, executive summaries, and learning stories from live portfolio data.
        </p>
      </div>

      <Card>
        <CardTitle>Generate narrative</CardTitle>
        <CardDescription>Draft text you can refine before publishing to reports.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="name">Title</Label>
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="type">Type</Label>
            <select
              id="type"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={narrativeType}
              onChange={(e) => setNarrativeType(e.target.value)}
            >
              <option value="executive_summary">Executive summary</option>
              <option value="donor_update">Donor update</option>
              <option value="success_story">Success story</option>
              <option value="lessons_learned">Lessons learned</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="prompt">Optional prompt</Label>
            <Input
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Emphasize community health outcomes and verified evidence"
            />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Generating…" : "Generate"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Generated narratives</CardTitle>
        <div className="mt-4 space-y-4">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-stone-200 p-4 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-medium">{item.name}</h3>
                  <p className="font-mono text-xs text-stone-400">{item.code}</p>
                </div>
                <div className="flex gap-2">
                  <StatusBadge status={item.narrative_type} />
                  <StatusBadge status={item.status} />
                </div>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm text-stone-600 dark:text-stone-300">
                {item.content}
              </p>
              <p className="mt-2 text-xs text-stone-400">
                {item.provider}
                {item.model ? ` · ${item.model}` : ""}
              </p>
            </div>
          ))}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No narratives yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
